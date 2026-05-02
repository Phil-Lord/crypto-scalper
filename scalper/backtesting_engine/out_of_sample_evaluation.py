import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from typing import Callable, Generator

import optuna
import pandas as pd
from tqdm import tqdm

from data_system import (
    OutOfSampleEvaluation,
    OutOfSampleEvaluationRepository,
    SQLAlchemyClient,
    SQLAlchemyOutOfSampleEvaluationRepository,
    SQLAlchemyTradeRepository
)
from strategy_manager import create_strategy
from utils import OptunaConfig

from .backtesting_engine import BacktestingEngine
from .parameter_optimisation import create_windows
from .window_evaluation import evaluate_param_set_over_windows

logger = logging.getLogger(__name__)


INITIAL_BALANCE = 1000

PAIR = 'XXBTZGBP'
STRATEGY_NAME = 'PrecisionTrendStrategy'


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
        parameter set evaluated. When ``None``, the library installs a default
        tqdm-backed progress bar to preserve existing CLI behaviour.
    '''
    study = load_study(study_name)

    client = SQLAlchemyClient()
    eval_repo = SQLAlchemyOutOfSampleEvaluationRepository(client)

    evaluated_trials = eval_repo.get_evaluated_trial_numbers(study_name, start, end)
    top_param_sets = get_top_param_sets(study, num_sets, evaluated_trials)
    if len(top_param_sets) == 0:
        return

    windows = create_windows(start, end)

    if n_workers <= 1:
        engine = build_engine(PAIR, STRATEGY_NAME, top_param_sets[0]['params'], start, end)
        results = run_evaluation(engine, top_param_sets, windows, progress_callback)
    else:
        results = run_evaluation_parallel(
            PAIR, STRATEGY_NAME, top_param_sets, windows, start, end, n_workers, progress_callback
        )

    save_results(eval_repo, results, study_name, start, end)


def load_study(study_name: str) -> optuna.Study:
    logger.info(f'Loading study: {study_name}')
    storage = optuna.storages.RDBStorage(
        url=OptunaConfig.DB_URL,
        engine_kwargs={
            'pool_pre_ping': True,
            'connect_args': {
                'application_name': 'out_of_sample_evaluation',
                'keepalives_idle': 30
            }
        }
    )
    return optuna.load_study(study_name=study_name, storage=storage)


def get_top_param_sets(study: optuna.Study, n: int, evaluated_trials: set[int]) -> list[dict]:
    logger.info(f'Extracting top {n} parameter sets from study...')
    completed_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    reverse = study.direction == optuna.study.StudyDirection.MAXIMIZE
    top_trials = sorted(completed_trials, key=lambda t: t.value, reverse=reverse)[:n]
    top_trials = [t for t in top_trials if t.number not in evaluated_trials]
    logger.info(f'Selected {len(top_trials)} new parameter sets for evaluation.')

    top_param_sets = [
        {
            'trial_number': t.number,
            'value': t.value,
            'params': t.params
        }
        for t in top_trials
    ]
    return top_param_sets


def build_engine(pair: str, strategy_name: str, params: dict, start: float, end: float) -> BacktestingEngine:
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
    with _resolve_progress_callback(progress_callback, len(top_param_sets)) as on_tick:
        for param_set in top_param_sets:
            results.append(evaluate_param_set(engine, param_set, windows))
            on_tick()
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
        'geo_mean_return': geometric_mean_ratio,
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
    with _resolve_progress_callback(progress_callback, len(top_param_sets)) as on_tick:
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
                for _ in chunk_results:
                    on_tick()
    return results


@contextmanager
def _resolve_progress_callback(
    progress_callback: Callable[[], None] | None,
    total: int,
) -> Generator[Callable[[], None], None, None]:
    '''
    Yield a ``() -> None`` tick callback. When ``progress_callback`` is ``None``,
    install a default tqdm bar that closes on exit so existing CLI behaviour
    (a single 'Evaluating' progress bar) is preserved.
    '''
    if progress_callback is not None:
        yield progress_callback
        return
    pbar = tqdm(total=total, desc='Evaluating', dynamic_ncols=True, bar_format='{l_bar}{bar}')
    try:
        yield lambda: pbar.update(1)
    finally:
        pbar.close()


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
            geo_mean_return=result['geo_mean_return']
        )
        for result in results
    ]
    repository.add(evaluations)
