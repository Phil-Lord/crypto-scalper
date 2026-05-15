'''
Walk-forward UI service.

Orchestrates the in-sample / out-of-sample subprocesses via
:func:`core.run_subprocess`, parsing each stdout line through
:func:`core.parse` into the shared :class:`core.StreamEvent` contract that
``scripts/optimise_in_sample.py`` and ``scripts/evaluate_out_of_sample.py``
emit. argv for each subprocess is built by ``build_in_sample_command`` /
``build_out_of_sample_command`` colocated with the optimisation entry points
in :mod:`backtesting_engine`.

The two phases share a single module because they share both the event
contract and the surrounding lifecycle (``Job`` rows, cancellation, progress
streaming).

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
from collections.abc import Callable, Iterable
from pathlib import Path

import optuna

from backtesting_engine import (
    OOS_OVERFIT_THRESHOLD,
    build_in_sample_command,
    build_out_of_sample_command,
    get_top_param_sets,
    load_study as _load_study_from_storage
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
from ui.models.walk_forward import (
    StudyDirection,
    StudySummary,
    TrialVerdict,
    TrialWithOos,
)
from utils import OptunaConfig


SCALPER_DIR = Path(__file__).resolve().parents[2]


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


async def start_in_sample(
    pair: str,
    strategy_name: str,
    start: str,
    end: str,
    n_trials: int,
    n_workers: int,
    job_repo: JobRepository,
    on_progress: Callable[[int, StreamEvent], None] | None = None,
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
    splits = split_trials(n_trials, n_workers)
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
    on_progress: Callable[[StreamEvent], None] | None = None,
) -> Job:
    '''
    Run an out-of-sample evaluation as a single subprocess.

    Parallelism happens inside the script's ``ProcessPoolExecutor``, so this
    layer only spawns one OS process and creates one ``Job`` row.
    '''
    job = Job(job_type=JobType.EVALUATE_OUT_OF_SAMPLE)
    cmd = build_out_of_sample_command(study_name, num_sets, start, end, n_workers)

    def callback(line: str) -> None:
        event = parse(line)
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


def list_oos_windows(
    study_name: str,
    oos_repo: OutOfSampleEvaluationRepository,
) -> list[OosWindowAggregate]:
    '''
    Aggregate the OOS evaluation table by ``(start_timestamp, end_timestamp)``
    for a single study, applying ``OOS_OVERFIT_THRESHOLD`` to split each
    window's trials into generalised vs overfit counts.

    :return: One aggregate per evaluated window, ordered by start timestamp.
        Empty if the study has no OOS evaluations yet.
    '''
    return oos_repo.aggregate_windows(study_name, OOS_OVERFIT_THRESHOLD)


def get_top_trials(study_name: str, n: int) -> list[dict]:
    '''
    Return the top ``n`` completed trials of a study, highest objective first
    (or lowest if the study minimises).

    Used by the OOS tab to preview which parameter sets the script would
    evaluate. Includes already-evaluated trials (the preview shows the full
    selection, not the to-do list).
    '''
    return get_top_param_sets(load_study(study_name), n)


def get_top_trials_with_oos(
    study_name: str,
    window: tuple[float, float] | None,
    n_trials: int,
    oos_repo: OutOfSampleEvaluationRepository,
) -> list[TrialWithOos]:
    '''
    Top ``n_trials`` trials for a study, left-joined with OOS scores from ``window``.

    Trials are picked by Optuna direction (max vs min); the OOS join adds a
    ``delta`` (``oos - is``) and ``verdict`` per row. ``window=None`` returns
    the top trials with every row marked ``PENDING`` — used by the page when
    no OOS window has been selected yet.

    :param window: ``(start, end)`` Unix seconds matching one of
        :func:`list_oos_windows`'s rows, or ``None``.
    '''
    study = load_study(study_name)
    top_trials = get_top_param_sets(study, n_trials)

    if window is None:
        oos_by_trial: dict[int, float] = {}
    else:
        evaluations = oos_repo.get(study_name, window[0], window[1])
        oos_by_trial = {e.trial_number: e.geo_mean_return for e in evaluations}

    return [
        _to_trial_with_oos(trial, oos_by_trial.get(trial['trial_number']))
        for trial in top_trials
    ]


def get_trial_params(study_name: str, trial_number: int) -> dict:
    '''
    Return the params dict for a single trial. Used by the page's
    copy-params button as a lazy-fetch fallback when the bulk prefetch
    is unavailable.
    '''
    study = load_study(study_name)
    for trial in study.trials:
        if trial.number == trial_number:
            return trial.params
    raise KeyError(f'Trial {trial_number} not found in study {study_name}')


def get_trial_params_bulk(study_name: str, trial_numbers: Iterable[int]) -> dict[int, dict]:
    '''
    Return ``{trial_number: params}`` for every requested trial in a single
    pass over ``study.trials``. Used by the OOS panel's eager prefetch so
    loading N rows is O(study.trials) rather than O(N * study.trials).

    Missing trial numbers are silently omitted — callers fall back to a
    per-click lookup via :func:`get_trial_params`.
    '''
    needed = set(trial_numbers)
    if not needed:
        return {}
    study = load_study(study_name)
    return {
        trial.number: trial.params
        for trial in study.trials
        if trial.number in needed
    }


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


def split_trials(n_trials: int, n_workers: int) -> list[int]:
    '''
    Split ``n_trials`` across ``n_workers``, distributing the remainder to the
    first workers. Returns one positive trial count per active worker — workers
    that would receive zero trials are dropped.

    Public so the IS panel can seed its worker grid with the same per-worker
    trial counts the run will actually use.
    '''
    if n_trials <= 0 or n_workers <= 0:
        return []
    workers = min(n_workers, n_trials)
    base, remainder = divmod(n_trials, workers)
    return [base + (1 if i < remainder else 0) for i in range(workers)]


def _make_progress_handler(
    index: int,
    on_progress: Callable[[int, StreamEvent], None] | None,
) -> Callable[[str], None]:
    def handler(line: str) -> None:
        event = parse(line)
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


def _to_trial_with_oos(trial: dict, oos_score: float | None) -> TrialWithOos:
    '''
    Join a trial dict with its OOS score to produce a TrialWithOos for the UI.

    :param trial: Dict with keys ``trial_number``, ``value``, and ``params``.
    :param oos_score: Geo-mean return for the trial in the selected OOS window, or
        ``None`` if the trial has not been evaluated in that window yet.
    '''
    is_value = trial['value']
    if oos_score is None:
        delta = None
        verdict = TrialVerdict.PENDING
    else:
        delta = oos_score - is_value
        verdict = (
            TrialVerdict.GENERALISES
            if oos_score >= OOS_OVERFIT_THRESHOLD
            else TrialVerdict.OVERFIT
        )

    return TrialWithOos(
        trial_number=trial['trial_number'],
        is_value=is_value,
        oos_score=oos_score,
        delta=delta,
        verdict=verdict,
        params=trial['params']
    )
