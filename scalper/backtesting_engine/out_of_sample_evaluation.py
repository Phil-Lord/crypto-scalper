import logging
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
from typing import Callable

import optuna
import pandas as pd

from data_system import (
    OutOfSampleEvaluation,
    OutOfSampleEvaluationRepository,
    SQLAlchemyClient,
    SQLAlchemyOutOfSampleEvaluationRepository,
    SQLAlchemyTradeRepository
)
from strategy_manager import create_strategy
from utils import load_study, parse_study_name

from .backtesting_engine import BacktestingEngine
from .parameter_optimisation import create_windows
from .window_evaluation import evaluate_param_set_over_windows

logger = logging.getLogger(__name__)


INITIAL_BALANCE = 1000

'''
Geometric mean OOS balance-ratio cutoff: a trial generalises when
``oos_geo_mean_balance_ratio >= OOS_OVERFIT_THRESHOLD``, otherwise it is overfit.

This lives here on the domain layer because robustness is a backtesting concept;
the walk-forward UI just renders the verdict.
'''
OOS_OVERFIT_THRESHOLD = 0.5


class TrialVerdict(str, Enum):
    '''
    Generalisation verdict for a trial against an OOS window.

    ``PENDING`` — trial has no OOS evaluation in the chosen window yet.
    ``GENERALISES`` — OOS geo-mean return at or above ``OOS_OVERFIT_THRESHOLD``.
    ``OVERFIT`` — OOS geo-mean return below ``OOS_OVERFIT_THRESHOLD``.
    '''
    PENDING = 'pending'
    GENERALISES = 'generalises'
    OVERFIT = 'overfit'


@dataclass(frozen=True)
class TrialWithOos:
    '''
    Top-trial row joined with its OOS score for a selected window.

    Attributes:
        trial_number (int): Optuna trial number.
        is_value (float): In-sample objective value.
        oos_score (float | None): OOS geo-mean return for the chosen window, or
            ``None`` if the trial has not been evaluated in that window yet.
        delta (float | None): ``oos_score - is_value``;
            ``None`` when ``oos_score`` is ``None``.
        verdict (TrialVerdict): Pending / generalises / overfit.
        params (dict): Trial parameter dict (same shape as ``trial.params``).
    '''
    trial_number: int
    is_value: float
    oos_score: float | None
    delta: float | None
    verdict: TrialVerdict
    params: dict


def build_out_of_sample_command(
    study_name: str,
    num_sets: int,
    start: str,
    end: str,
    n_workers: int = 1,
) -> list[str]:
    '''
    Build the argv to invoke the out-of-sample evaluation as
    ``python -m scripts.evaluate_out_of_sample``.

    Colocated with the evaluation entry point so flag changes update one place.
    Used by ``ui.services.walk_forward`` to spawn the evaluation subprocess.
    '''
    return [
        sys.executable, '-m', 'scripts.evaluate_out_of_sample',
        '-sn', study_name,
        '-n', str(num_sets),
        '-s', start,
        '-e', end,
        '-w', str(n_workers),
    ]


def evaluate_out_of_sample(
    study_name: str,
    num_sets: int,
    start: float,
    end: float,
    n_workers: int = 1,
    progress_callback: Callable[[], None] | None = None,
) -> None:
    '''
    Evaluate top parameter sets from an optimisation study on a new time period.

    Tests how well optimised parameters generalise to unseen data by running
    them on a different time range and computing performance metrics.

    :param study_name: Name of the Optuna study to load top trials from.
    :param num_sets: Number of top trials to evaluate.
    :param start: Out-of-sample period start (Unix seconds).
    :param end: Out-of-sample period end (Unix seconds).
    :param n_workers: Number of worker processes for parallel evaluation. Default
        ``1`` runs serially in-process. Values >1 distribute ``top_param_sets``
        across ``ProcessPoolExecutor`` workers, each constructing its own
        ``BacktestingEngine`` (and loading OHLC data) once.
    :param progress_callback: Optional ``() -> None`` callback invoked once per
        parameter set evaluated. Entry points pick presentation; the library
        installs no default progress bar.
    '''
    parsed = parse_study_name(study_name)
    study = load_study(study_name, application_name='out_of_sample_evaluation')

    client = SQLAlchemyClient()
    eval_repo = SQLAlchemyOutOfSampleEvaluationRepository(client)

    evaluated_trials = eval_repo.get_evaluated_trial_numbers(study_name, start, end)
    top_param_sets = get_top_param_sets(study, num_sets, evaluated_trials)
    if len(top_param_sets) == 0:
        return

    windows = create_windows(start, end)

    if n_workers <= 1:
        # Seed params are a placeholder; engine.strategy is replaced per param set
        # inside evaluate_param_set_over_windows.
        engine = build_engine(
            parsed.kraken_pair, parsed.strategy, top_param_sets[0]['params'], start, end
        )
        results = run_evaluation(engine, top_param_sets, windows, progress_callback)
    else:
        results = run_evaluation_parallel(
            parsed.kraken_pair, parsed.strategy, top_param_sets, windows,
            start, end, n_workers, progress_callback
        )

    save_results(eval_repo, results, study_name, start, end)


def get_top_param_sets(
    study: optuna.Study, n: int, evaluated_trials: set[int] | None = None
) -> list[dict]:
    '''
    Return the top ``n`` completed trials of ``study`` as parameter-set dicts,
    highest objective first (or lowest if the study minimises).

    :param evaluated_trials: Trial numbers to exclude (already evaluated). Pass
        ``None`` to include every completed trial — used by the UI preview which
        shows what *would* be evaluated, regardless of prior evaluation state.
    '''
    logger.info(f'Extracting top {n} parameter sets from study...')
    completed_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    reverse = study.direction == optuna.study.StudyDirection.MAXIMIZE
    top_trials = sorted(completed_trials, key=lambda t: t.value, reverse=reverse)[:n]
    if evaluated_trials is not None:
        top_trials = [t for t in top_trials if t.number not in evaluated_trials]
    logger.info(f'Selected {len(top_trials)} parameter sets for evaluation.')

    return [
        {'trial_number': t.number, 'value': t.value, 'params': t.params}
        for t in top_trials
    ]


def get_top_trials_with_oos(
    study: optuna.Study,
    window: tuple[float, float] | None,
    n_trials: int,
    oos_repo: OutOfSampleEvaluationRepository,
) -> list[TrialWithOos]:
    '''
    Top ``n_trials`` trials of ``study``, left-joined with OOS scores from ``window``.

    Trials are picked by Optuna direction (max vs min); the OOS join adds a
    ``delta`` (``oos - is``) and ``verdict`` per row. ``window=None`` returns
    the top trials with every row marked ``PENDING`` — used by callers that
    want a preview before an OOS window has been selected.

    :param window: ``(start, end)`` Unix seconds matching one of the rows
        returned by :meth:`OutOfSampleEvaluationRepository.aggregate_windows`,
        or ``None``.
    '''
    top_trials = get_top_param_sets(study, n_trials)

    if window is None:
        oos_by_trial: dict[int, float] = {}
    else:
        evaluations = oos_repo.get(study.study_name, window[0], window[1])
        oos_by_trial = {e.trial_number: e.geo_mean_balance_ratio for e in evaluations}

    return [
        _to_trial_with_oos(trial, oos_by_trial.get(trial['trial_number']))
        for trial in top_trials
    ]


def _to_trial_with_oos(trial: dict, oos_score: float | None) -> TrialWithOos:
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


def build_engine(
        pair: str,
        strategy_name: str,
        params: dict,
        start: float,
        end: float
) -> BacktestingEngine:
    client = SQLAlchemyClient()
    trade_repo = SQLAlchemyTradeRepository(client)
    strategy = create_strategy(strategy_name, params)
    return BacktestingEngine(
        pair=pair,
        strategy=strategy,
        repository=trade_repo,
        start=start,
        end=end,
        interval=1,
        vectorised=True,
    )


def run_evaluation(
    engine: BacktestingEngine,
    top_param_sets: list[dict],
    windows: list[tuple[pd.Timestamp, pd.Timestamp]],
    progress_callback: Callable[[], None] | None = None,
) -> list[dict]:
    results = []
    for param_set in top_param_sets:
        results.append(evaluate_param_set(engine, param_set, windows))
        if progress_callback is not None:
            progress_callback()
    return results


def evaluate_param_set(
    engine: BacktestingEngine,
    param_set: dict,
    windows: list[tuple[pd.Timestamp, pd.Timestamp]],
) -> dict:
    window_balances = evaluate_param_set_over_windows(
        engine, param_set['params'], windows, INITIAL_BALANCE
    )
    geometric_mean = pd.Series(window_balances).prod() ** (1 / len(window_balances))
    geometric_mean_ratio = float(geometric_mean / INITIAL_BALANCE)
    return {
        'trial_number': param_set['trial_number'],
        'geo_mean_balance_ratio': geometric_mean_ratio,
    }


def run_evaluation_parallel(
    pair: str,
    strategy_name: str,
    top_param_sets: list[dict],
    windows: list[tuple[pd.Timestamp, pd.Timestamp]],
    start: float,
    end: float,
    n_workers: int,
    progress_callback: Callable[[], None] | None = None
) -> list[dict]:
    chunks = chunk_param_sets(top_param_sets, n_workers)

    results = []
    with ProcessPoolExecutor(max_workers=len(chunks)) as executor:
        futures = [
            executor.submit(
                _evaluate_chunk_worker, pair, strategy_name, chunk, windows, start, end
            )
            for chunk in chunks
        ]
        for future in as_completed(futures):
            chunk_results = future.result()
            results.extend(chunk_results)
            if progress_callback is not None:
                for _ in chunk_results:
                    progress_callback()
    return results


def chunk_param_sets(param_sets: list[dict], n_chunks: int) -> list[list[dict]]:
    '''
    Split ``param_sets`` into at most ``n_chunks`` near-equal chunks.

    Empty chunks are not produced — if ``n_chunks`` exceeds ``len(param_sets)``
    only ``len(param_sets)`` chunks are returned, one item each.
    '''
    num_param_sets = len(param_sets)
    num_chunks = min(max(n_chunks, 1), num_param_sets)
    base = num_param_sets // num_chunks
    remainder = num_param_sets % num_chunks

    chunks = []
    i = 0
    for c in range(num_chunks):
        size = base + (1 if c < remainder else 0)
        chunks.append(param_sets[i:i + size])
        i += size
    return chunks


def _evaluate_chunk_worker(
    pair: str,
    strategy_name: str,
    param_sets_chunk: list[dict],
    windows: list[tuple[pd.Timestamp, pd.Timestamp]],
    start: float,
    end: float,
) -> list[dict]:
    '''
    Process-pool worker. Builds one engine per worker process (loading OHLC
    once) and evaluates every assigned parameter set against it.
    '''
    # Seed params are a placeholder; engine.strategy is replaced per param set
    # inside evaluate_param_set_over_windows.
    engine = build_engine(pair, strategy_name, param_sets_chunk[0]['params'], start, end)
    return [evaluate_param_set(engine, ps, windows) for ps in param_sets_chunk]


def save_results(
    repository: OutOfSampleEvaluationRepository,
    results: list[dict],
    study_name: str,
    start: float,
    end: float
) -> None:
    evaluations = [
        OutOfSampleEvaluation(
            study_name=study_name,
            trial_number=result['trial_number'],
            start_timestamp=start,
            end_timestamp=end,
            geo_mean_balance_ratio=result['geo_mean_balance_ratio']
        )
        for result in results
    ]
    repository.add(evaluations)
