'''
Walk-forward UI service.

Builds CLI commands, parses the shared ``PROGRESS`` / ``DONE`` JSON contract
emitted by ``scripts/optimise_in_sample.py`` and ``scripts/evaluate_out_of_sample.py``,
and orchestrates subprocess execution via :func:`core.run_subprocess`.

The two phases share a single module because they share both the JSON contract
and the surrounding lifecycle (``Job`` rows, cancellation, progress streaming).
'''
import asyncio
import json
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

import optuna

from core import run_subprocess
from data_system import (
    Job,
    JobRepository,
    JobType,
    OutOfSampleEvaluation,
    SQLAlchemyClient,
    SQLAlchemyOutOfSampleEvaluationRepository,
)
from utils import OptunaConfig


SCALPER_DIR = Path(__file__).resolve().parents[2]


ProgressEvent = dict
'''
Parsed progress line: ``{'event': 'PROGRESS' | 'DONE', 'payload': dict}``.
'''


def build_in_sample_command(
    pair: str,
    strategy_name: str,
    start: str,
    end: str,
    n_trials: int,
    n_jobs: int = 1,
) -> list[str]:
    '''
    Build the argv for ``scripts.optimise_in_sample``.

    The script is invoked via ``-m scripts.optimise_in_sample`` so it can be run
    from the ``scalper/`` directory without requiring ``PYTHONPATH`` to be set.
    '''
    return [
        sys.executable, '-m', 'scripts.optimise_in_sample',
        '-p', pair,
        '-sn', strategy_name,
        '-s', start,
        '-e', end,
        '-n', str(n_trials),
        '-j', str(n_jobs),
    ]


def build_out_of_sample_command(
    study_name: str,
    num_sets: int,
    start: str,
    end: str,
    n_workers: int = 1,
) -> list[str]:
    '''
    Build the argv for ``scripts.evaluate_out_of_sample``.
    '''
    return [
        sys.executable, '-m', 'scripts.evaluate_out_of_sample',
        '-sn', study_name,
        '-n', str(num_sets),
        '-s', start,
        '-e', end,
        '-w', str(n_workers),
    ]


def parse_progress(line: str) -> ProgressEvent | None:
    '''
    Parse one stdout line emitted by the walk-forward CLI scripts.

    Both scripts emit lines of the form ``EVENT {json-payload}`` where ``EVENT``
    is ``PROGRESS`` or ``DONE``. Returns ``None`` for anything else (blank
    lines, log noise, malformed JSON) so callers can ignore non-contract output.
    '''
    if not line:
        return None
    parts = line.strip().split(' ', 1)
    if len(parts) != 2:
        return None
    event, raw_payload = parts
    if event not in ('PROGRESS', 'DONE'):
        return None
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return {'event': event, 'payload': payload}


async def start_in_sample(
    pair: str,
    strategy_name: str,
    start: str,
    end: str,
    n_trials: int,
    n_workers: int,
    job_repo: JobRepository,
    on_progress: Callable[[int, ProgressEvent], None] | None = None,
) -> list[Job]:
    '''
    Run an in-sample Optuna optimisation as ``n_workers`` parallel subprocesses.

    Trials are split as evenly as possible across workers. Each worker runs in
    its own OS process with its own ``Job(JobType.OPTIMISE_IN_SAMPLE)`` row, and
    contributes trials to the same Optuna study (the script resolves the study
    name deterministically from the pair / strategy / time window).

    :param on_progress: ``(worker_index, parsed_event)`` invoked for each
        ``PROGRESS`` / ``DONE`` line emitted by any worker. Non-contract lines
        are dropped.
    :return: The N ``Job`` instances that were created (already passed through
        ``run_subprocess`` and persisted by the time this returns).

    Cancelling the awaiting task propagates ``CancelledError`` to each worker's
    ``run_subprocess`` call, which terminates the underlying subprocess and
    marks the job ``ERROR``. Optuna persists per-trial, so completed trials are
    retained.
    '''
    splits = _split_trials(n_trials, n_workers)
    jobs = [Job(job_type=JobType.OPTIMISE_IN_SAMPLE) for _ in splits]
    coroutines: list[Awaitable[None]] = []
    for index, (job, n_trials) in enumerate(zip(jobs, splits)):
        cmd = build_in_sample_command(pair, strategy_name, start, end, n_trials, n_jobs=1)
        callback = _make_progress_handler(index, on_progress)
        coroutines.append(
            run_subprocess(job_repo, job, cmd, on_progress=callback, cwd=str(SCALPER_DIR))
        )
    await asyncio.gather(*coroutines)
    return jobs


async def start_out_of_sample(
    study_name: str,
    num_sets: int,
    start: str,
    end: str,
    n_workers: int,
    job_repo: JobRepository,
    on_progress: Callable[[ProgressEvent], None] | None = None,
) -> Job:
    '''
    Run an out-of-sample evaluation as a single subprocess.

    Parallelism happens inside the script's ``ProcessPoolExecutor``, so this
    layer only spawns one OS process and creates one ``Job`` row.
    '''
    job = Job(job_type=JobType.EVALUATE_OUT_OF_SAMPLE)
    cmd = build_out_of_sample_command(study_name, num_sets, start, end, n_workers)

    def callback(line: str) -> None:
        event = parse_progress(line)
        if event is not None and on_progress is not None:
            on_progress(event)

    await run_subprocess(job_repo, job, cmd, on_progress=callback, cwd=str(SCALPER_DIR))
    return job


def get_top_trials(study_name: str, n: int) -> list[dict]:
    '''
    Return the top ``n`` completed trials of a study, highest objective first
    (or lowest if the study minimises).

    Each entry is ``{'trial_number': int, 'value': float, 'params': dict}``.
    Used by the OOS tab to preview which parameter sets the script would
    evaluate. Read-only — does not write to Optuna or the SQLite eval table.
    '''
    storage = optuna.storages.RDBStorage(url=OptunaConfig.DB_URL)
    study = optuna.load_study(study_name=study_name, storage=storage)
    completed = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    reverse = study.direction == optuna.study.StudyDirection.MAXIMIZE
    top = sorted(completed, key=lambda t: t.value, reverse=reverse)[:n]
    return [
        {'trial_number': t.number, 'value': t.value, 'params': t.params}
        for t in top
    ]


def get_evaluation_results(
    study_name: str, start: float, end: float
) -> list[OutOfSampleEvaluation]:
    '''
    Read previously persisted out-of-sample evaluation rows for a study and
    time window.
    '''
    repo = SQLAlchemyOutOfSampleEvaluationRepository(SQLAlchemyClient())
    return repo.get(study_name, start, end)


def _split_trials(n_trials: int, n_workers: int) -> list[int]:
    '''
    Split ``n_trials`` across ``n_workers``, distributing the remainder to the
    first workers. Returns one positive trial count per active worker — workers
    that would receive zero trials are dropped.
    '''
    if n_trials <= 0 or n_workers <= 0:
        return []
    workers = min(n_workers, n_trials)
    base, remainder = divmod(n_trials, workers)
    return [base + (1 if i < remainder else 0) for i in range(workers)]


def _make_progress_handler(
    index: int,
    on_progress: Callable[[int, ProgressEvent], None] | None,
) -> Callable[[str], None]:
    def handler(line: str) -> None:
        event = parse_progress(line)
        if event is not None and on_progress is not None:
            on_progress(index, event)
    return handler
