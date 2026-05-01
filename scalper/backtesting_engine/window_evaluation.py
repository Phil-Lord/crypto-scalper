from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from strategy_manager import create_strategy

if TYPE_CHECKING:
    from .backtesting_engine import BacktestingEngine


def evaluate_param_set_over_windows(
    engine: 'BacktestingEngine',
    params: dict[str, Any],
    windows: list[tuple[pd.Timestamp, pd.Timestamp]],
    initial_balance: float = 1000,
) -> list[float]:
    '''
    Evaluate a parameter set across multiple OHLC windows.

    Constructs the strategy from `params` once, then, for each window:
    1. resets strategy state
    2. slices the engine's OHLC data to the window
    3. runs the strategy
    4. captures the final quote balance

    Shared by the in-sample optimisation objective and the out-of-sample
    evaluator to keep the per-window run mechanics in one place.

    :param engine: BacktestingEngine pre-loaded with OHLC data spanning the windows.
    :param params: Strategy parameters.
    :param windows: List of (start, end) timestamps to evaluate over.
    :param initial_balance: Starting quote balance for each window.
    :return: Final quote balance for each window, in order.
    '''
    strategy_name = type(engine.strategy).__name__
    engine.strategy = create_strategy(strategy_name, params)

    balances = []
    for start, end in windows:
        run_strategy_on_window(engine, start, end)
        balances.append(engine.get_final_quote_balance(initial_balance))
    return balances


def run_strategy_on_window(
    engine: 'BacktestingEngine',
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> None:
    '''
    Reset strategy state, slice the engine's OHLC data to the window, and run.

    Used per-window by `evaluate_param_set_over_windows` and by the IS
    objective's loop (which needs to inspect `engine.results` between windows
    for penalty calculation, so cannot use the wrapper end-to-end).
    '''
    engine.strategy.reset()
    engine.set_ohlc_window(start, end)
    engine.run()
