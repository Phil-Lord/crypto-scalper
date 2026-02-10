import numpy as np
import pandas as pd

from data_system import Signal

from .base_rule import Rule


class MaCrossoverRule(Rule):
    def __init__(self, short_ma_name: str, long_ma_name: str):
        self.short_ma_name = short_ma_name
        self.long_ma_name = long_ma_name

    def check(self, current_state: dict) -> Signal:
        short_ma = current_state[self.short_ma_name]
        long_ma = current_state[self.long_ma_name]
        prev_short_ma = current_state.get(f'prev_{self.short_ma_name}', None)
        prev_long_ma = current_state.get(f'prev_{self.long_ma_name}', None)

        if None in (short_ma, long_ma, prev_short_ma, prev_long_ma):
            return Signal.HOLD

        if (short_ma > long_ma) and (prev_short_ma <= prev_long_ma):
            return Signal.BUY
        elif (short_ma < long_ma) and (prev_short_ma >= prev_long_ma):
            return Signal.SELL
        return Signal.HOLD

    def compute_vectorised(self, results: pd.DataFrame) -> pd.Series:
        short_ma = results[self.short_ma_name]
        long_ma = results[self.long_ma_name]

        cross_above = (short_ma > long_ma) & (short_ma.shift(1) <= long_ma.shift(1))
        cross_below = (short_ma < long_ma) & (short_ma.shift(1) >= long_ma.shift(1))

        signals = np.full(len(results), 'hold', dtype=object)
        signals[cross_above] = 'buy'
        signals[cross_below] = 'sell'
        return pd.Series(signals, index=results.index)
