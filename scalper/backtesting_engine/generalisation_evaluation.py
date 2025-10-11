import optuna
import pandas as pd
from tqdm import tqdm

from .backtesting_engine import BacktestingEngine
from .objective import run_strategy_on_window
from .parameter_optimisation import create_windows
from utils import get_second_timestamp, OPTUNA_DB_URL


INITIAL_BALANCE = 1000


def find_params(study_name: str) -> None:
    study = load_study(study_name)
    top_param_sets = get_top_param_sets(study, 5)

    start = get_second_timestamp(2025, 1, 1)
    end = get_second_timestamp(2025, 9, 1)
    windows = create_windows(start, end)

    engine = BacktestingEngine(
        pair='XXBTZGBP',
        strategy_name='PrecisionTrendStrategy',
        start=start,
        end=end,
        interval=1,
        vectorised=True,
        **top_param_sets[0]['params']
    )

    results = run_evaluation(engine, top_param_sets, windows)
    return calculate_mean_returns(results)


def load_study(study_name: str) -> optuna.Study:
    print(f'Loading study: {study_name}')
    storage = optuna.storages.RDBStorage(
        url=OPTUNA_DB_URL,
        engine_kwargs={
            'pool_pre_ping': True,
            'connect_args': {
                'application_name': 'generalisation_evaluation',
                'keepalives_idle': 30
            }
        }
    )
    return optuna.load_study(study_name=study_name, storage=storage)


def get_top_param_sets(study: optuna.Study, n: int = 5) -> list[dict]:
    print(f'Extracting top {n} parameter sets from study...')
    completed_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    reverse = study.direction == optuna.study.StudyDirection.MAXIMIZE
    top_trials = sorted(completed_trials, key=lambda t: t.value, reverse=reverse)[:n]
    top_param_sets = [
        {
            "trial_number": t.number,
            "value": t.value,
            "params": t.params
        }
        for t in top_trials
    ]
    return top_param_sets


def run_evaluation(engine: BacktestingEngine, top_param_sets: list[dict], windows: list[tuple[int, int]]) -> list[dict]:
    results = []
    with tqdm(total=len(top_param_sets), desc=f'Evaluating', dynamic_ncols=True, bar_format='{l_bar}{bar}') as pbar:
        for param_set in top_param_sets:
            window_balances = []
            for window_start, window_end in windows:
                run_strategy_on_window(engine, param_set['params'], window_start, window_end)
                final_balance = engine.get_final_quote_balance(INITIAL_BALANCE)
                window_balances.append(final_balance)
            results.append({
                'trial_number': param_set['trial_number'],
                'window_balances': window_balances
            })
        pbar.update(1)
    return results


def calculate_mean_returns(results: list[dict]) -> list[dict]:
    mean_trial_returns = []
    for result in results:
        trial_balances = result['window_balances']
        geometric_mean = pd.Series(trial_balances).prod() ** (1 / len(trial_balances))
        geometric_mean_ratio = float(geometric_mean / INITIAL_BALANCE)
        mean_trial_returns.append({
            'trial_number': result['trial_number'],
            'geo_mean_return': geometric_mean_ratio
        })
    return sorted(mean_trial_returns, key=lambda x: x['geo_mean_return'], reverse=True)
