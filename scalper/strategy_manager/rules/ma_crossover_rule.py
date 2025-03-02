import pandas as pd

from .base_rule import Rule


class MaCrossoverRule(Rule):
    def __init__(self, short_ma: str, long_ma: str):
        self.short_ma = short_ma
        self.long_ma = long_ma

    def check(self, current_state: dict) -> str:
        short_ma = current_state[self.short_ma]
        long_ma = current_state[self.long_ma]
        prev_short_ma = current_state.get(f'prev_{self.short_ma}', None)
        prev_long_ma = current_state.get(f'prev_{self.long_ma}', None)

        if short_ma is None or long_ma is None or prev_short_ma is None or prev_long_ma is None:
            return 'hold'

        cross_above = (short_ma > long_ma) and (prev_short_ma <= prev_long_ma)
        cross_below = (short_ma < long_ma) and (prev_short_ma >= prev_long_ma)

        if cross_above and current_state['last_action'] != 'buy':
            return 'buy'
        elif cross_below and current_state['last_action'] == 'buy':
            return 'sell'
        return 'hold'

    def compute_vectorised(self, results: pd.DataFrame) -> pd.Series:
        ''' Generate signals based on short and long MAs across the entire trading run. '''
        short_ma = results[self.short_ma]
        long_ma = results[self.long_ma]
        cross_above = (short_ma > long_ma) & (short_ma.shift(1) <= long_ma.shift(1))
        cross_below = (short_ma < long_ma) & (short_ma.shift(1) >= long_ma.shift(1))

        signals = pd.Series('hold', index=results.index)
        signals[cross_above] = 'buy'
        signals[cross_below] = 'sell'
        return signals
