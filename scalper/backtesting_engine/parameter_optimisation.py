import os
import sqlite3
import warnings

import optuna
from optuna.exceptions import ExperimentalWarning
import pandas as pd
from tqdm import tqdm

from utils import OPTUNA_DB_URL
from strategy_manager import StrategyManager


def get_objective(engine, param_grid: dict[str, list[any]], constraints: list[callable] = None) -> callable:
    def objective(trial: optuna.Trial) -> float:
        ''' Optimisation Objective: Maximise final quote balance. '''
        params = {}
        for name, (low, high) in param_grid.items():
            if isinstance(low, int):
                params[name] = trial.suggest_int(name, low, high)
            elif isinstance(low, float):
                params[name] = trial.suggest_float(name, low, high)
            else:
                raise ValueError(f'Unsupported parameter type for {name}')

        if constraints:
            for constraint in constraints:
                if not constraint(params):
                    raise optuna.TrialPruned()

        engine.strategy = StrategyManager().get_strategy(engine.strategy.__class__.__name__, **params)
        engine.run()
        return engine.get_final_quote_balance()
    return objective


def optimise_parameters(engine, param_grid: dict[str, list[any]], n_trials: int = 100) -> dict[str, any]:
    db_dir = os.path.join(os.path.dirname(__file__))
    os.makedirs(db_dir, exist_ok=True)
    db_url = f'sqlite:///{db_dir}/optimisation_shared/optimisation.db'

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(
        direction='maximize',
        sampler=optuna.samplers.TPESampler(
            n_startup_trials=10,
            multivariate=True,
            group=True,
            constant_liar=True
        ),
        storage=db_url,
        load_if_exists=True
    )

    # Enable Write-Ahead Logging (WAL) mode
    conn = sqlite3.connect(f'{db_dir}/optimisation_shared/optimisation.db')
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")  # Better performance than FULL
    conn.close()

    study.optimize(get_objective(engine, param_grid), n_trials=n_trials, n_jobs=-1)
    return {'best_params': study.best_params, 'best_profit': study.best_value, 'study': study}


def optimise_parameters_postgres(engine, param_grid: dict[str, list[any]], n_trials: int = 100,
                                 constraints: list[callable] = None) -> dict[str, any]:
    warnings.filterwarnings("ignore", category=ExperimentalWarning)

    # Create study name using backtest params.
    study_name = (
        f'{engine.strategy.__class__.__name__}_'
        f'{engine.pair}_'
        f'{pd.to_datetime(engine.start, unit='s').strftime('%Y%m%d')}-'
        f'{pd.to_datetime(engine.end, unit='s').strftime('%Y%m%d')}'
    )

    # Create postgres Optuna storage instance.
    storage = optuna.storages.RDBStorage(
        url=OPTUNA_DB_URL,
        engine_kwargs={
            'pool_size': 10,
            'max_overflow': 10,
            'pool_pre_ping': True,
            'connect_args': {
                'application_name': f'worker_{os.getpid()}',  # For PgAdmin monitoring.
                'keepalives_idle': 30  # Prevent timeouts.
            }
        }
    )

    # Create study.
    try:
        study = optuna.create_study(
            study_name=study_name,
            storage=storage,
            load_if_exists=True,
            direction='maximize',
            sampler=optuna.samplers.TPESampler(
                n_startup_trials=min(20, n_trials//5),  # Dynamic startup.
                multivariate=True,
                group=True,
                constant_liar=True
            )
        )
    except optuna.exceptions.DuplicatedStudyError:
        # Handle concurrent study creation.
        study = optuna.load_study(study_name=study_name, storage=storage)

    # Run optimisation.
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    progress_callback = TqdmProgressCallback(n_trials)
    try:
        study.optimize(
            get_objective(engine, param_grid, constraints),
            n_trials=n_trials,
            n_jobs=-1,
            callbacks=[progress_callback]
        )
    finally:
        progress_callback.close()
    return {'best_params': study.best_params, 'best_profit': study.best_value, 'study': study}


class TqdmProgressCallback:
    def __init__(self, total_trials: int):
        self.pbar = tqdm(total=total_trials, desc="Optimising", dynamic_ncols=True)

    def __call__(self, study: optuna.study.Study, trial: optuna.trial.FrozenTrial) -> None:
        self.pbar.update(1)

    def close(self) -> None:
        self.pbar.close()
