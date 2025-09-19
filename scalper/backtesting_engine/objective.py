import optuna
import pandas as pd
import numpy as np

from strategy_manager import StrategyManager


def get_objective(engine, param_grid: dict[str, list[any]], constraints: list[callable] = None,
                  windows: list[tuple[pd.Timestamp, pd.Timestamp]] = None) -> callable:
    def objective(trial: optuna.Trial) -> float:
        ''' Optimisation Objective: Maximise geometric mean of per-window return ratios. '''
        params = suggest_parameters(trial, param_grid)
        prune_invalid_trials(constraints, params)

        # --- Optimisation setup --- #
        initial_balance = 1000
        adjusted_window_returns = []

        # --- Window-based optimisation --- #
        for window_start, window_end in windows:
            # Strategy definition
            engine.strategy = StrategyManager().get_strategy(engine.strategy.__class__.__name__, **params)

            # Run strategy on window and calculate return ratio.
            engine.set_ohlc_window(window_start, window_end)
            engine.run()
            final_balance = engine.get_final_quote_balance(initial_balance)
            window_return = (final_balance / initial_balance)  # e.g. 1.05 = +5%

            # --- Per-window logistic activity penalty --- #
            results = engine.results
            trade_count = results['signal'].ne('hold').sum()
            duration_days = (window_end - window_start).days or 1
            ideal_trade_count = duration_days * 0.3  # Target: 0.3 trades/day.

            # Logistic penalty: smoothly increases as trade_count approaches ideal
            k = 0.01  # steepness of curve
            penalty = 1 / (1 + np.exp(-k * (trade_count - ideal_trade_count)))

            # Apply penalty to return
            adjusted_return = window_return * penalty
            adjusted_window_returns.append(adjusted_return)
            trial.set_user_attr(
                f"trades_{window_start.date()}_{window_end.date()}", int(trade_count))

        # --- Calculate geometric mean of return ratios to account for compounding --- #
        avg_return = pd.Series(adjusted_window_returns).prod() ** (1 / len(adjusted_window_returns))
        return avg_return
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


def prune_invalid_trials(constraints: list[callable], params: dict[str, list[any]]) -> None:
    ''' Prune trials that violate constraints. '''
    if constraints:
        for constraint in constraints:
            if not constraint(params):
                raise optuna.TrialPruned()
