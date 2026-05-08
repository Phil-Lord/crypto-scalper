'''
Walk-forward UI service.

Parses the shared ``PROGRESS`` / ``DONE`` JSON contract emitted by
``scripts/optimise_in_sample.py`` and ``scripts/evaluate_out_of_sample.py`` and
orchestrates subprocess execution via :func:`core.run_subprocess`.
Each script exposes its own ``build_command`` colocated with the click options.

The two phases share a single module because they share both the JSON contract
and the surrounding lifecycle (``Job`` rows, cancellation, progress streaming).

Also exposes read-only helpers the redesigned walk-forward page consumes:

- study summaries
- OOS-window aggregates
- top trials joined with OOS scores
- single-trial param lookups.

``load_study`` results are cached in-process so the page can rerender
without paying the Optuna round-trip; :func:`invalidate_study_cache`
lets the page drop entries when a phase finishes.

TODO: Update the wording here once the page is redesigned.
'''
import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import optuna
from sqlalchemy import text

from backtesting_engine import (
    OOS_OVERFIT_THRESHOLD,
    get_top_param_sets,
    load_study as _load_study_from_storage
)
from core import run_subprocess
from data_system import (
    Job,
    JobRepository,
    JobType,
    OutOfSampleEvaluation,
    SQLAlchemyClient,
    SQLAlchemyOutOfSampleEvaluationRepository,
)
from scripts.evaluate_out_of_sample import build_command as build_out_of_sample_command
from scripts.optimise_in_sample import build_command as build_in_sample_command
from utils import OptunaConfig


SCALPER_DIR = Path(__file__).resolve().parents[2]


# Parsed progress line: ``{'event': 'PROGRESS' | 'DONE', 'payload': dict}``.
ProgressEvent = dict


class StudyDirection(str, Enum):
    ''' Optimisation direction for an Optuna study. '''
    MAXIMIZE = 'maximize'
    MINIMIZE = 'minimize'

@dataclass(frozen=True)
class StudySummary:
    '''
    Summary row for the studies rail.

    Attributes:
        name (str): Optuna study name.
        pair (str): Trading pair parsed from the study name.
        strategy (str): Strategy class name parsed from the study name.
        trial_count (int): Total trials recorded against the study.
        best_is (float | None): Best in-sample objective value, or ``None`` if
            the study has no completed trial yet.
        direction (StudyDirection): Optimisation direction.

    Note:
        Does not include ``last_run_state`` — that is a UI concern merged in by
        the page from in-process state.
    '''
    name: str
    pair: str
    strategy: str
    trial_count: int
    best_is: float | None
    direction: StudyDirection


@dataclass(frozen=True)
class OosWindowSummary:
    '''
    Aggregate of OOS evaluations for a single (start, end) window.

    Attributes:
        start (float): Window start (Unix seconds).
        end (float): Window end (Unix seconds).
        best_oos (float): Highest geo-mean OOS return across evaluated trials.
        generalised_count (int): Trials with OOS at or above ``OOS_OVERFIT_THRESHOLD``.
        overfit_count (int): Trials with OOS below ``OOS_OVERFIT_THRESHOLD``.
    '''
    start: float
    end: float
    best_oos: float
    generalised_count: int
    overfit_count: int


_study_cache: dict[str, optuna.Study] = {}


def load_study(study_name: str) -> optuna.Study:
    '''
    Return a cached :class:`optuna.Study` for ``study_name``, loading it on
    first access. Subsequent calls reuse the cached instance — call
    :func:`invalidate_study_cache` after a phase finishes to pick up new trials.
    '''
    if study_name not in _study_cache:
        _study_cache[study_name] = _load_study_from_storage(study_name)
    return _study_cache[study_name]


def invalidate_study_cache(study_name: str | None = None) -> None:
    '''
    Drop cached :class:`optuna.Study` instances.

    :param study_name: If provided, drop only that study; otherwise clear the
        whole cache. Missing entries are a no-op.
    '''
    if study_name is None:
        _study_cache.clear()
    else:
        _study_cache.pop(study_name, None)


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
    retained. If one worker raises a non-cancellation exception (e.g. a spawn
    failure), the remaining workers are cancelled and their subprocesses
    terminated before the exception propagates, so no orphaned children leak.
    '''
    splits = _split_trials(n_trials, n_workers)
    jobs = [Job(job_type=JobType.OPTIMISE_IN_SAMPLE) for _ in splits]
    tasks: list[asyncio.Task[None]] = []
    for index, (job, worker_trials) in enumerate(zip(jobs, splits)):
        cmd = build_in_sample_command(pair, strategy_name, start, end, worker_trials, n_jobs=1)
        callback = _make_progress_handler(index, on_progress)
        tasks.append(asyncio.create_task(
            run_subprocess(job_repo, job, cmd, on_progress=callback, cwd=str(SCALPER_DIR))
        ))
    try:
        await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
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


def list_studies_with_summary() -> list[StudySummary]:
    '''
    Return a summary row for every Optuna study in storage, ordered by name.

    Pair and strategy are parsed from the study name's
    ``{Strategy}_{pair}_{YYYYMMDD-YYYYMMDD}`` shape; legacy or hand-renamed
    studies that don't match are returned with empty pair/strategy strings.
    '''
    storage = optuna.storages.RDBStorage(url=OptunaConfig.DB_URL)
    summaries = optuna.get_all_study_summaries(storage)
    return [_to_study_summary(summary) for summary in summaries]


def list_oos_windows(study_name: str) -> list[OosWindowSummary]:
    '''
    Aggregate the OOS evaluation table by ``(start_timestamp, end_timestamp)``
    for a single study.

    :return: One summary model per evaluated window, ordered by start timestamp.
        Empty if the study has no OOS evaluations yet.
    '''
    client = SQLAlchemyClient()
    with client.session() as session:
        rows = session.execute(
            text(
                '''
                SELECT
                    start_timestamp,
                    end_timestamp,
                    MAX(geo_mean_return) AS best_oos,
                    SUM(CASE WHEN geo_mean_return >= :threshold THEN 1 ELSE 0 END) AS generalised,
                    SUM(CASE WHEN geo_mean_return < :threshold THEN 1 ELSE 0 END) AS overfit
                FROM out_of_sample_evaluation
                WHERE study_name = :study_name
                GROUP BY start_timestamp, end_timestamp
                ORDER BY start_timestamp
                '''
            ),
            {'study_name': study_name, 'threshold': OOS_OVERFIT_THRESHOLD},
        ).fetchall()
    return [
        OosWindowSummary(
            start=row[0],
            end=row[1],
            best_oos=row[2],
            generalised_count=int(row[3]),
            overfit_count=int(row[4]),
        )
        for row in rows
    ]


def get_top_trials(study_name: str, n: int) -> list[dict]:
    '''
    Return the top ``n`` completed trials of a study, highest objective first
    (or lowest if the study minimises).

    Used by the OOS tab to preview which parameter sets the script would
    evaluate. Includes already-evaluated trials (the preview shows the full
    selection, not the to-do list).
    '''
    return get_top_param_sets(load_study(study_name), n)


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


def _to_study_summary(summary: optuna.study.StudySummary) -> StudySummary:
    # Extract details from study name (Strategy_pair_yyymmdd-yyymmdd)
    name_parts = summary.study_name.rsplit('_', 2)
    strategy = name_parts[0] if len(name_parts) == 3 else ''
    pair = name_parts[1] if len(name_parts) == 3 else ''

    direction = (
        StudyDirection.MAXIMIZE
        if summary.direction == optuna.study.StudyDirection.MAXIMIZE
        else StudyDirection.MINIMIZE
    )
    best_is = summary.best_trial.value if summary.best_trial is not None else None

    return StudySummary(
        name=summary.study_name,
        pair=pair,
        strategy=strategy,
        trial_count=summary.n_trials,
        best_is=best_is,
        direction=direction,
    )
