from typing import Any, Callable

import optuna
import pandas as pd
import numpy as np

INITIAL_BALANCE = 1000


def get_objective(
        engine,
        param_grid: dict[str, list[Any]],
        windows: list[tuple[pd.Timestamp, pd.Timestamp]] = None
) -> Callable:
    def objective(trial: optuna.Trial) -> float:
        ''' Optimisation Objective: Maximise geometric mean of per-window return ratios. '''
        params = suggest_parameters(trial, param_grid)
        adjusted_window_returns = []

        for window_start, window_end in windows:
            run_strategy_on_window(engine, params, window_start, window_end)

            # Calculate penalty.
            trade_count = engine.results['signal'].ne('hold').sum()
            penalty = calculate_penalty(trade_count, window_start, window_end)
            log_window_trial_count(trial, window_start, window_end, trade_count)

            # Calculate return ratio and apply penalty.
            final_balance = engine.get_final_quote_balance(INITIAL_BALANCE)
            adjusted_window_returns.append(calculate_adjusted_return(final_balance, penalty))

        return calculate_geometric_mean(adjusted_window_returns)
    return objective


def suggest_parameters(trial: optuna.Trial, param_grid: dict[str, list[Any]]) -> dict[str, Any]:
    ''' Suggest a value for each parameter in the grid. '''
    params = {}
    for name, (low, high) in param_grid.items():
        if isinstance(low, int) and isinstance(high, int):
            params[name] = trial.suggest_int(name, low, high)
        elif isinstance(low, float) or isinstance(high, float):
            params[name] = trial.suggest_float(name, float(low), float(high))
        else:
            raise ValueError(f'Unsupported parameter type for {name}')
    return params


def run_strategy_on_window(engine, params: dict[str, Any], start: pd.Timestamp, end: pd.Timestamp) -> None:
    ''' Configure and run the strategy on an OHLC window. '''
    config_cls = type(engine.strategy.config)
    strategy_cls = type(engine.strategy)

    try:
        new_config = config_cls(**params)
    except ValueError:
        raise optuna.TrialPruned()

    engine.strategy = strategy_cls(new_config)
    engine.set_ohlc_window(start, end)
    engine.run()


def calculate_penalty(trade_count: int, start: pd.Timestamp, end: pd.Timestamp) -> float:
    '''
    Calculate per-window logistic activity penalty, which adapts smoothly with trade count.
    - Ideal trade count is 0.3 trades/day.
    - Penalty multiplier scales from x0 (no trades) to x1 (ideal and above).
    '''
    duration_days = (end - start).days or 1
    ideal_trade_count = duration_days * 0.3  # Target: 0.3 trades/day
    k = 0.02  # Steepness of curve (0.02 is reasonably forgiving)
    raw = 1 / (1 + np.exp(-k * (trade_count - ideal_trade_count)))  # Scale to [0,1], ideal = 0.5
    return min(1.0, raw * 2)  # Scale to [0,2], cap = 1, ideal = 1


def log_window_trial_count(trial: optuna.Trial, start: pd.Timestamp, end: pd.Timestamp, count: int) -> None:
    ''' Log window trade count as user attribute. '''
    trial.set_user_attr(f'trades_{start.date()}_{end.date()}', int(count))


def calculate_adjusted_return(final_balance: float, penalty: float) -> float:
    ''' Calculate return ratio adjusted by penalty. '''
    window_return = final_balance / INITIAL_BALANCE  # e.g. 1005 / 1000 = 1.05 (+5%)
    return window_return * penalty


def calculate_geometric_mean(returns: list[float]) -> float:
    ''' Calculate geometric mean of return ratios to account for compounding. '''
    return pd.Series(returns).prod() ** (1 / len(returns))
