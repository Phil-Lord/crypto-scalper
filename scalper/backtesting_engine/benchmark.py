import pandas as pd


def buy_and_hold_ratio(window: pd.DataFrame, fee: float = 0.004) -> float:
    '''
    Final-to-initial balance ratio for buying at the first bar and holding to the last.

    Buys at the first bar's close and sells at the last bar's close, charging the
    trading fee on both sides. Fills on 'close' to match the strategy's signal price
    (see `base_strategy`). The ratio is independent of starting balance, so it can be
    used directly as the per-window benchmark in a relative objective:
    `strategy_ratio / buy_and_hold_ratio`.

    :param window: OHLC DataFrame with a 'close' column, indexed by timestamp.
    :param fee: Per-side trading fee as a fraction, e.g. 0.004 taker, 0.0016 maker
        (default: 0.004).
    :return: Final balance divided by initial balance for a buy-and-hold position.
    '''
    if window.empty:
        raise ValueError('Cannot compute buy-and-hold ratio over an empty window.')

    first_close = window['close'].iloc[0]
    last_close = window['close'].iloc[-1]
    return (last_close / first_close) * (1 - fee) ** 2


def buy_and_hold_equity_curve(
    window: pd.DataFrame, initial_quote_balance: float = 1000, fee: float = 0.004
) -> pd.Series:
    '''
    Mark-to-market equity curve for a buy-and-hold position over the window.

    Buys at the first bar's close (charging the entry fee) and values the position at
    each bar's close, net of the exit fee. The exit fee is applied at every point as a
    constant scaling, so bar-to-bar returns are unaffected and the final value equals
    `initial_quote_balance * buy_and_hold_ratio(window, fee)` exactly. Aligned to the
    window's index so it can be plotted against, or differenced alongside, a strategy
    equity curve.

    :param window: OHLC DataFrame with a 'close' column, indexed by timestamp.
    :param initial_quote_balance: Starting balance in quote currency (default: 1000).
    :param fee: Per-side trading fee as a fraction, e.g. 0.004 taker, 0.0016 maker
        (default: 0.004).
    :return: Equity-curve Series indexed like `window`, in quote currency.
    '''
    if window.empty:
        raise ValueError('Cannot compute buy-and-hold equity curve over an empty window.')

    first_close = window['close'].iloc[0]
    return initial_quote_balance * (window['close'] / first_close) * (1 - fee) ** 2
