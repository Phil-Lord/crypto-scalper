import numpy as np
import pandas as pd

from .base_rule import Rule


class MaCrossoverRule(Rule):
    def __init__(self, short_ma: str, long_ma: str):
        self.short_ma = short_ma
        self.long_ma = long_ma

    def check(self, current_state: dict) -> str:
        short_ma = current_state[self.short_ma]
        long_ma = current_state[self.long_ma]

        if short_ma is None or long_ma is None:
            return 'hold'

        if short_ma > long_ma and current_state['position'] != 'long':
            return 'buy'
        elif short_ma < long_ma and current_state['position'] == 'long':
            return 'sell'
        return 'hold'

    def compute_vectorised(self, data: pd.DataFrame) -> pd.Series:
        short_ma = data[self.short_ma]
        long_ma = data[self.long_ma]
        cross_above = (short_ma > long_ma) & (short_ma.shift(1) <= long_ma.shift(1))
        cross_below = (short_ma < long_ma) & (short_ma.shift(1) >= long_ma.shift(1))

        signals = pd.Series('hold', index=data.index)
        signals[cross_above] = 'buy'
        signals[cross_below] = 'sell'
        return signals
