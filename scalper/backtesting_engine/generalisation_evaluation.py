import optuna
import pandas as pd
import sqlite3
from tqdm import tqdm

from .backtesting_engine import BacktestingEngine
from .objective import run_strategy_on_window
from .parameter_optimisation import create_windows
from strategy_manager import StrategyManager
from utils import GEN_EVAL_DB_PATH, OPTUNA_DB_URL


INITIAL_BALANCE = 1000


def find_params(study_name: str, num_sets: int, start: float, end: float) -> None:
    study = load_study(study_name)
    evaluated_trials = get_evaluted_trials(study_name, start, end)
    top_param_sets = get_top_param_sets(study, num_sets, evaluated_trials)
    if len(top_param_sets) == 0:
        return

    engine = BacktestingEngine(
        pair='XXBTZGBP',
        strategy_name='PrecisionTrendStrategy',
        start=start,
        end=end,
        interval=1,
        vectorised=True,
        **top_param_sets[0]['params']
    )

    windows = create_windows(start, end)
    results = run_evaluation(engine, top_param_sets, windows)
    save_results_to_db(results, study_name, start, end)


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


def get_evaluted_trials(study_name: str, start: float, end: float) -> set[int]:
    conn = sqlite3.connect(GEN_EVAL_DB_PATH)
    cursor = conn.cursor()
    create_table(cursor)

    query = '''
        SELECT trial_number FROM generalisation_evaluation
        WHERE study_name = ? AND start_timestamp = ? AND end_timestamp = ?
    '''
    cursor.execute(query, (study_name, start, end))
    rows = cursor.fetchall()
    conn.close()

    evaluated_trials = {row[0] for row in rows}
    return evaluated_trials


def get_top_param_sets(study: optuna.Study, n: int, evaluated_trials: set[int]) -> list[dict]:
    print(f'Extracting top {n} parameter sets from study...')
    completed_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    reverse = study.direction == optuna.study.StudyDirection.MAXIMIZE
    top_trials = sorted(completed_trials, key=lambda t: t.value, reverse=reverse)[:n]
    top_trials = [t for t in top_trials if t.number not in evaluated_trials]
    print(f'Selected {len(top_trials)} new parameter sets for evaluation.')

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
            # Run on full period first
            engine.set_ohlc_window()
            engine.strategy = StrategyManager().get_strategy(
                engine.strategy.__class__.__name__, **param_set['params'])
            engine.run()
            final_quote_balance = engine.get_final_quote_balance(INITIAL_BALANCE)

            # Run on each window
            window_balances = []
            for window_start, window_end in windows:
                run_strategy_on_window(engine, param_set['params'], window_start, window_end)
                final_balance = engine.get_final_quote_balance(INITIAL_BALANCE)
                window_balances.append(final_balance)

            # Calculate mean return across windows
            geometric_mean = pd.Series(window_balances).prod() ** (1 / len(window_balances))
            geometric_mean_ratio = float(geometric_mean / INITIAL_BALANCE)

            # Store results
            results.append({
                'trial_number': param_set['trial_number'],
                'final_balance': float(final_quote_balance),
                'geo_mean_return': geometric_mean_ratio
            })
            pbar.update(1)
    return results


def save_results_to_db(results: list[dict], study_name: str, start: float, end: float) -> None:
    conn = sqlite3.connect(GEN_EVAL_DB_PATH)
    cursor = conn.cursor()
    create_table(cursor)

    query = '''
        INSERT OR REPLACE INTO generalisation_evaluation (
            study_name, trial_number, start_timestamp, end_timestamp, final_balance, geo_mean_return
        ) VALUES (?, ?, ?, ?, ?, ?)
    '''
    cursor.executemany(
        query,
        [
            (
                study_name,
                result['trial_number'],
                start,
                end,
                result.get('final_balance', None),
                result.get('geo_mean_return', None)
            )
            for result in results
        ]
    )
    conn.commit()
    conn.close()


def create_table(cursor: sqlite3.Cursor) -> None:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS generalisation_evaluation (
            study_name TEXT,
            trial_number INTEGER,
            start_timestamp REAL,
            end_timestamp REAL,
            final_balance REAL,
            geo_mean_return REAL,
            PRIMARY KEY (study_name, trial_number, start_timestamp, end_timestamp)
        )
    ''')
