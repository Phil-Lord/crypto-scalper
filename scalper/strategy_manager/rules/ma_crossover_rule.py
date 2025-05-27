import pandas as pd

from .base_rule import Rule


class MaCrossoverRule(Rule):
    def __init__(self, short_ma_name: str, long_ma_name: str):
        self.short_ma_name = short_ma_name
        self.long_ma_name = long_ma_name

    def check(self, current_state: dict) -> str:
        ''' Generate a signal based on the current and previous MAs and the last action.  '''
        short_ma = current_state[self.short_ma_name]
        long_ma = current_state[self.long_ma_name]
        prev_short_ma = current_state.get(f'prev_{self.short_ma_name}', None)
        prev_long_ma = current_state.get(f'prev_{self.long_ma_name}', None)

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
        short_ma = results[self.short_ma_name]
        long_ma = results[self.long_ma_name]
        cross_above = (short_ma > long_ma) & (short_ma.shift(1) <= long_ma.shift(1))
        cross_below = (short_ma < long_ma) & (short_ma.shift(1) >= long_ma.shift(1))

        signals = pd.Series('hold', index=results.index)
        last_action = 'sell'
        for i in range(len(results)):
            if cross_above.iloc[i] and last_action != 'buy':
                signals.iloc[i] = 'buy'
                last_action = 'buy'
            elif cross_below.iloc[i] and last_action == 'buy':
                signals.iloc[i] = 'sell'
                last_action = 'sell'
        return signals
