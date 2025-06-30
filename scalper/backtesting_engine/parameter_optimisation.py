import os
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


def optimise_parameters(engine, param_grid: dict[str, list[any]], n_trials: int = 100,
                        constraints: list[callable] = None) -> dict[str, any]:
    warnings.filterwarnings("ignore", category=ExperimentalWarning)
    study_name = create_study_name(engine)
    storage = create_storage()
    study = create_study(storage, study_name, n_trials)
    optimise(n_trials, study, engine, param_grid, constraints)
    return {'best_params': study.best_params, 'best_profit': study.best_value, 'study': study}


def create_study_name(engine) -> str:
    return (
        f'{engine.strategy.__class__.__name__}_'
        f'{engine.pair}_'
        f'{pd.to_datetime(engine.start, unit='s').strftime('%Y%m%d')}-'
        f'{pd.to_datetime(engine.end, unit='s').strftime('%Y%m%d')}'
    )


def create_storage() -> optuna.storages.RDBStorage:
    return optuna.storages.RDBStorage(
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


def create_study(storage, study_name: str, n_trials: int) -> optuna.study.Study:
    try:
        return optuna.create_study(
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
        return optuna.load_study(study_name=study_name, storage=storage)


def optimise(n_trials: int, study: optuna.study.Study, engine, param_grid: dict[str, list[any]],
             constraints: list[callable] = None) -> None:
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


class TqdmProgressCallback:
    def __init__(self, total_trials: int):
        self.pbar = tqdm(total=total_trials, desc="Optimising", dynamic_ncols=True)

    def __call__(self, study: optuna.study.Study, trial: optuna.trial.FrozenTrial) -> None:
        self.pbar.update(1)

    def close(self) -> None:
        self.pbar.close()
