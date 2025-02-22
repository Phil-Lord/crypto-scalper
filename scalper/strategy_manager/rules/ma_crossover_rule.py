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
        # Q: What's going on here?
        return pd.Series(
            np.where(data[self.short_ma] > data[self.long_ma], 'buy',
                     np.where(data[self.short_ma] < data[self.long_ma], 'sell', 'hold')),
            index=data.index
        )
