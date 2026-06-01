import os
from typing import Any, Callable
import warnings

import optuna
from optuna.exceptions import ExperimentalWarning
import pandas as pd

from .objective import get_objective
from utils import create_study_name, OptunaConfig


OptunaCallback = Callable[[optuna.study.Study, optuna.trial.FrozenTrial], None]


def optimise_parameters(
    engine,
    param_grid: dict[str, list[Any]],
    n_trials: int = 100,
    progress_callback: OptunaCallback | None = None,
) -> None:
    '''
    Run an Optuna parameter optimisation on the engine's strategy.

    :param engine: BacktestingEngine pre-loaded with OHLC data.
    :param param_grid: Search space, ``{name: [low, high]}``.
    :param n_trials: Number of Optuna trials.
    :param progress_callback: Optional Optuna callback ``(study, trial) -> None``
        invoked after each trial. Entry points pick presentation; the library
        installs no default progress bar.
    '''
    warnings.filterwarnings('ignore', category=ExperimentalWarning)
    windows = create_windows(engine.start, engine.end)
    study_name = create_study_name(
        engine.strategy.__class__.__name__, engine.pair, engine.start, engine.end,
    )
    storage = create_storage()
    study = create_study(storage, study_name, n_trials)
    validate_search_space(study, param_grid)
    optimise(n_trials, study, engine, windows, param_grid, progress_callback)


def create_storage() -> optuna.storages.RDBStorage:
    return optuna.storages.RDBStorage(
        url=OptunaConfig.DB_URL,
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


def create_study(storage: optuna.storages.RDBStorage, study_name: str, n_trials: int) -> optuna.study.Study:
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


def validate_search_space(study: optuna.study.Study, param_grid: dict[str, list[Any]]) -> None:
    ''' Validate param_grid matches existing study search space. '''
    trials = study.get_trials(deepcopy=False)
    if not trials:
        return

    param_dists = trials[-1].distributions
    if set(param_grid.keys()) != set(param_dists.keys()):
        raise ValueError('Parameter names conflict with existing study search space.')

    for name, (low, high) in param_grid.items():
        expected_low = low if isinstance(low, int) and isinstance(high, int) else float(low)
        expected_high = high if isinstance(low, int) and isinstance(high, int) else float(high)
        if param_dists[name].low != expected_low or param_dists[name].high != expected_high:
            raise ValueError('Parameter ranges conflict with existing study search space.')


def create_windows(start: float, end: float) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    '''
    Generate a list of rolling 3-month windows between two timestamps.

    - Each window spans exactly 3 calendar months.
    - Windows step forward by 1 month.
    - From the second window onward, the start is shifted back by 1 day (warmup).
    - The end of each window is exclusive, represented as (logical_end - 1 second).
    - Incomplete windows beyond the provided end timestamp are discarded.
    '''
    months_in_window = 3
    step_months = 1
    warmup_days = 1

    start_ts = pd.Timestamp(start, unit='s').round('ms')
    end_ts = pd.Timestamp(end, unit='s').round('ms')

    if end_ts < (start_ts + pd.DateOffset(months=months_in_window)):
        raise ValueError(f'Time range must be at least {months_in_window} months for optimisation.')

    windows = []

    i = 0
    while True:
        # Window end = start + 3 months - 1 second
        window_end = start_ts + pd.DateOffset(months=months_in_window) - pd.Timedelta(seconds=1)

        # Stop if window exceeds end
        if window_end > end_ts:
            break

        # Apply warmup for all but the first window
        window_start = start_ts if i == 0 else start_ts - pd.Timedelta(days=warmup_days)

        windows.append((window_start, window_end))

        # Step forward 1 month
        start_ts += pd.DateOffset(months=step_months)
        i += 1

    return windows


def optimise(
    n_trials: int,
    study: optuna.study.Study,
    engine,
    windows: list[tuple[pd.Timestamp, pd.Timestamp]],
    param_grid: dict[str, list[Any]],
    progress_callback: OptunaCallback | None = None,
) -> None:
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    callbacks = [progress_callback] if progress_callback is not None else []
    study.optimize(
        get_objective(engine, param_grid, windows),
        n_trials=n_trials,
        n_jobs=1,
        callbacks=callbacks,
    )
