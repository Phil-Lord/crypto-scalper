import optuna
import pandas as pd
import numpy as np

from strategy_manager import StrategyManager

INITIAL_BALANCE = 1000


def get_objective(engine, param_grid: dict[str, list[any]], constraints: list[callable] = None,
                  windows: list[tuple[pd.Timestamp, pd.Timestamp]] = None) -> callable:
    def objective(trial: optuna.Trial) -> float:
        ''' Optimisation Objective: Maximise geometric mean of per-window return ratios. '''
        params = suggest_parameters(trial, param_grid)
        if parameters_violate_constraints(constraints, params):
            raise optuna.TrialPruned()

        # --- Window-based optimisation --- #
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


def suggest_parameters(trial: optuna.Trial, param_grid: dict[str, list[any]]) -> dict[str, any]:
    ''' Suggest a value for each parameter in the grid. '''
    params = {}
    for name, (low, high) in param_grid.items():
        if isinstance(low, int):
            params[name] = trial.suggest_int(name, low, high)
        elif isinstance(low, float):
            params[name] = trial.suggest_float(name, low, high)
        else:
            raise ValueError(f'Unsupported parameter type for {name}')
    return params


def parameters_violate_constraints(constraints: list[callable], params: dict[str, list[any]]) -> bool:
    ''' Check if parameters violate constraints. '''
    if constraints:
        for constraint in constraints:
            if not constraint(params):
                return True
    return False


def run_strategy_on_window(engine, params: dict[str, any], start: pd.Timestamp, end: pd.Timestamp) -> None:
    ''' Configure and run the strategy on an OHLC window. '''
    engine.strategy = StrategyManager().get_strategy(engine.strategy.__class__.__name__, **params)
    engine.set_ohlc_window(start, end)
    engine.run()


def calculate_penalty(trade_count: int, start: pd.Timestamp, end: pd.Timestamp) -> float:
    ''' Calculate per-window logistic activity penalty, which adapts smoothly with trade count. '''
    duration_days = (end - start).days or 1
    ideal_trade_count = duration_days * 0.3  # Target: 0.3 trades/day.
    k = 0.01  # steepness of curve
    return 1 / (1 + np.exp(-k * (trade_count - ideal_trade_count)))


def log_window_trial_count(trial: optuna.Trial, start: pd.Timestamp, end: pd.Timestamp, count: int) -> None:
    ''' Log window trade count as user attribute. '''
    trial.set_user_attr(f"trades_{start.date()}_{end.date()}", int(count))


def calculate_adjusted_return(final_balance: float, penalty: float) -> float:
    ''' Calculate return ratio adjusted by penalty. '''
    window_return = final_balance / INITIAL_BALANCE  # e.g. 1005 / 1000 = 1.05 (+5%)
    return window_return * penalty


def calculate_geometric_mean(returns: list[float]) -> float:
    ''' Calculate geometric mean of return ratios to account for compounding. '''
    return pd.Series(returns).prod() ** (1 / len(returns))
