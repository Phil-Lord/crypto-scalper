import logging

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


def evaluate_out_of_sample(study_name: str, num_sets: int, start: float, end: float) -> None:
    '''
    Evaluate top parameter sets from an optimisation study on a new time period.

    Tests how well optimised parameters generalise to unseen data by running
    them on a different time range and computing performance metrics.
    '''
    study = load_study(study_name)

    client = SQLAlchemyClient()
    eval_repo = SQLAlchemyOutOfSampleEvaluationRepository(client)
    trade_repo = SQLAlchemyTradeRepository(client)

    evaluated_trials = eval_repo.get_evaluated_trial_numbers(study_name, start, end)
    top_param_sets = get_top_param_sets(study, num_sets, evaluated_trials)
    if len(top_param_sets) == 0:
        return

    strategy = create_strategy('PrecisionTrendStrategy', top_param_sets[0]['params'])
    engine = BacktestingEngine(
        pair='XXBTZGBP',
        strategy=strategy,
        repository=trade_repo,
        start=start,
        end=end,
        interval=1,
        vectorised=True
    )

    windows = create_windows(start, end)
    results = run_evaluation(engine, top_param_sets, windows)
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


def run_evaluation(engine: BacktestingEngine, top_param_sets: list[dict], windows: list[tuple[int, int]]) -> list[dict]:
    results = []
    with tqdm(total=len(top_param_sets), desc=f'Evaluating', dynamic_ncols=True, bar_format='{l_bar}{bar}') as pbar:
        for param_set in top_param_sets:
            window_balances = evaluate_param_set_over_windows(
                engine, param_set['params'], windows, INITIAL_BALANCE
            )

            geometric_mean = pd.Series(window_balances).prod() ** (1 / len(window_balances))
            geometric_mean_ratio = float(geometric_mean / INITIAL_BALANCE)

            results.append({
                'trial_number': param_set['trial_number'],
                'geo_mean_return': geometric_mean_ratio
            })
            pbar.update(1)
    return results


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
