'''
Walk-forward UI service.

Orchestrates the in-sample / out-of-sample subprocesses via
:func:`core.run_subprocess`, parsing each stdout line through
:func:`core.parse` into the shared :class:`core.StreamEvent` contract that the
``backtesting_engine._in_sample_worker`` / ``_out_of_sample_worker`` modules
emit. argv for each subprocess is built by ``build_in_sample_command`` /
``build_out_of_sample_command`` colocated with the worker entry points in
:mod:`backtesting_engine`.

The two phases share a single module because they share both the event
contract and the surrounding lifecycle (``Job`` rows, cancellation, progress
streaming).

Also exposes read-only helpers the redesigned walk-forward page consumes:

- study summaries
- OOS-window aggregates
- top trials joined with OOS scores.

The read helpers are ``async`` and offload their blocking Optuna/DB work to
NiceGUI's thread pool via :func:`nicegui.run.io_bound`, so a read never blocks
the single UI event loop (which would drop the websocket). The synchronous
bodies live in private ``_*`` functions — the public coroutines are thin
offload wrappers. ``io_bound`` returns ``None`` if the awaiting task is
cancelled (client disconnect) or the app is stopping; the wrappers coerce that
to an empty result so callers never have to special-case it, and a torn-down
client is handled by the page's render guards.

Top-trial reads use a top-N query against the Optuna RDB
(:func:`backtesting_engine.get_top_param_sets`), so they stay cheap on studies
with tens of thousands of trials and no in-process study cache is needed — each
read returns fresh data without a full materialise.
'''
import asyncio
from collections.abc import Callable
from pathlib import Path

from nicegui import run

from backtesting_engine import (
    OOS_DRAWDOWN_LIMIT,
    OOS_FLOOR,
    build_in_sample_command,
    build_out_of_sample_command,
    get_top_param_sets,
    get_top_trials_with_oos as _get_top_trials_with_oos_from_engine,
    split_trials,
    TrialWithOos
)
from core import StreamEvent, parse, run_subprocess
from data_system import (
    Job,
    JobRepository,
    JobType,
    OosWindowAggregate,
    OutOfSampleEvaluation,
    OutOfSampleEvaluationRepository,
)
from utils import (
    list_studies as _list_studies_from_storage,
    StudySummary
)


SCALPER_DIR = Path(__file__).resolve().parents[2]


async def start_in_sample(
    pair: str,
    strategy_name: str,
    start: float,
    end: float,
    n_trials: int,
    n_workers: int,
    job_repo: JobRepository,
    on_progress: Callable[[int, StreamEvent], None] | None = None,
) -> list[Job]:
    '''
    Run an in-sample Optuna optimisation as ``n_workers`` parallel subprocesses.

    Trials are split as evenly as possible across workers. Each worker runs in
    its own OS process with its own ``Job(JobType.OPTIMISE_IN_SAMPLE)`` row, and
    contributes trials to the same Optuna study (the worker resolves the study
    name deterministically from the pair / strategy / time window).

    :param start: Window start, Unix seconds.
    :param end: Window end, Unix seconds.
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
    splits = split_trials(n_trials, n_workers)
    jobs = [Job(job_type=JobType.OPTIMISE_IN_SAMPLE) for _ in splits]
    tasks: list[asyncio.Task[None]] = []
    for index, (job, worker_trials) in enumerate(zip(jobs, splits)):
        cmd = build_in_sample_command(pair, strategy_name, start, end, worker_trials)
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
    start: float,
    end: float,
    n_workers: int,
    job_repo: JobRepository,
    on_progress: Callable[[StreamEvent], None] | None = None,
) -> Job:
    '''
    Run an out-of-sample evaluation as a single subprocess.

    Parallelism happens inside the worker's ``ProcessPoolExecutor``, so this
    layer only spawns one OS process and creates one ``Job`` row.

    :param start: Window start, Unix seconds.
    :param end: Window end, Unix seconds.
    '''
    job = Job(job_type=JobType.EVALUATE_OUT_OF_SAMPLE)
    cmd = build_out_of_sample_command(study_name, num_sets, start, end, n_workers)

    def callback(line: str) -> None:
        event = parse(line)
        if event is not None and on_progress is not None:
            on_progress(event)

    await run_subprocess(job_repo, job, cmd, on_progress=callback, cwd=str(SCALPER_DIR))
    return job


async def list_studies() -> list[StudySummary]:
    ''' Return a summary row for every Optuna study in storage, ordered by name. '''
    return await run.io_bound(_list_studies_from_storage) or []


def _list_oos_windows(
    study_name: str,
    oos_repo: OutOfSampleEvaluationRepository,
) -> list[OosWindowAggregate]:
    return oos_repo.aggregate_windows(study_name, OOS_FLOOR, OOS_DRAWDOWN_LIMIT)


async def list_oos_windows(
    study_name: str,
    oos_repo: OutOfSampleEvaluationRepository,
) -> list[OosWindowAggregate]:
    '''
    Aggregate the OOS evaluation table by ``(start_timestamp, end_timestamp)``
    for a single study, applying ``OOS_FLOOR`` and ``OOS_DRAWDOWN_LIMIT`` to
    split each window's trials into generalised vs overfit counts.

    :return: One aggregate per evaluated window, ordered by start timestamp.
        Empty if the study has no OOS evaluations yet.
    '''
    return await run.io_bound(_list_oos_windows, study_name, oos_repo) or []


def _get_top_trials(study_name: str, n: int) -> list[dict]:
    return get_top_param_sets(study_name, n)


async def get_top_trials(study_name: str, n: int) -> list[dict]:
    '''
    Return the top ``n`` completed trials of a study, highest objective first
    (or lowest if the study minimises).

    Used by the OOS tab to preview which parameter sets the script would
    evaluate. Includes already-evaluated trials (the preview shows the full
    selection, not the to-do list).
    '''
    return await run.io_bound(_get_top_trials, study_name, n) or []


def _get_top_trials_with_oos(
    study_name: str,
    window: tuple[float, float] | None,
    n_trials: int,
    oos_repo: OutOfSampleEvaluationRepository,
) -> list[TrialWithOos]:
    return _get_top_trials_with_oos_from_engine(
        study_name, window, n_trials, oos_repo,
    )


async def get_top_trials_with_oos(
    study_name: str,
    window: tuple[float, float] | None,
    n_trials: int,
    oos_repo: OutOfSampleEvaluationRepository,
) -> list[TrialWithOos]:
    '''
    Offloaded wrapper around :func:`backtesting_engine.get_top_trials_with_oos`.

    Each call runs a top-N query against the Optuna RDB, so it is cheap to call
    on every render and live tick even for a 100k-trial study. Returned rows
    already carry their ``params``, so callers read those directly rather than
    a separate per-trial lookup.
    '''
    return await run.io_bound(
        _get_top_trials_with_oos, study_name, window, n_trials, oos_repo,
    ) or []


def _get_trial_params(study_name: str, trial_number: int) -> dict:
    study = load_study(study_name)
    for trial in study.trials:
        if trial.number == trial_number:
            return trial.params
    raise KeyError(f'Trial {trial_number} not found in study {study_name}')


async def get_trial_params(study_name: str, trial_number: int) -> dict:
    '''
    Return the params dict for a single trial. Used by the page's
    copy-params button as a lazy-fetch fallback when the bulk prefetch
    is unavailable.
    '''
    return await run.io_bound(_get_trial_params, study_name, trial_number) or {}


def _get_trial_params_bulk(study_name: str, trial_numbers: Iterable[int]) -> dict[int, dict]:
    needed = set(trial_numbers)
    if not needed:
        return {}
    study = load_study(study_name)
    return {
        trial.number: trial.params
        for trial in study.trials
        if trial.number in needed
    }


async def get_trial_params_bulk(
    study_name: str, trial_numbers: Iterable[int]
) -> dict[int, dict]:
    '''
    Return ``{trial_number: params}`` for every requested trial in a single
    pass over ``study.trials``. Used by the OOS panel's eager prefetch so
    loading N rows is O(study.trials) rather than O(N * study.trials).

    Missing trial numbers are silently omitted — callers fall back to a
    per-click lookup via :func:`get_trial_params`.
    '''
    return await run.io_bound(
        _get_trial_params_bulk, study_name, list(trial_numbers),
    ) or {}


def get_evaluation_results(
    study_name: str,
    start: float,
    end: float,
    oos_repo: OutOfSampleEvaluationRepository,
) -> list[OutOfSampleEvaluation]:
    '''
    Read previously persisted out-of-sample evaluation rows for a study and
    time window.
    '''
    return oos_repo.get(study_name, start, end)


def _make_progress_handler(
    index: int,
    on_progress: Callable[[int, StreamEvent], None] | None,
) -> Callable[[str], None]:
    def handler(line: str) -> None:
        event = parse(line)
        if event is not None and on_progress is not None:
            on_progress(index, event)
    return handler
