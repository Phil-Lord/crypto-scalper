import pandas as pd

from .base_rule import Rule


class RsiThresholdRule(Rule):
    def __init__(self, rsi_name: str, oversold: float, overbought: float):
        self.rsi_name = rsi_name
        self.oversold = oversold
        self.overbought = overbought

    def check(self, current_state: dict) -> str:
        rsi = current_state[self.rsi_name]
        prev_rsi = current_state.get(f'prev_{self.rsi_name}', None)
        if rsi is None or prev_rsi is None:
            return 'hold'

        cross_above_oversold = (rsi < self.oversold) and (prev_rsi >= self.oversold)
        cross_below_overbought = (rsi > self.overbought) and (prev_rsi <= self.overbought)

        if cross_above_oversold and current_state['last_action'] != 'buy':
            return 'buy'
        elif cross_below_overbought and current_state['last_action'] == 'buy':
            return 'sell'
        return 'hold'

    def compute_vectorised(self, results: pd.DataFrame) -> pd.Series:
        rsi = results[self.rsi_name]
        cross_above_oversold = (rsi > self.oversold) & (rsi.shift(1) <= self.oversold)
        cross_below_overbought = (rsi < self.overbought) & (rsi.shift(1) >= self.overbought)

        signals = pd.Series('hold', index=results.index)
        last_action = 'sell'

        for i in range(len(results)):
            if cross_above_oversold.iloc[i] and last_action != 'buy':
                signals.iloc[i] = 'buy'
                last_action = 'buy'
            elif cross_below_overbought.iloc[i] and last_action == 'buy':
                signals.iloc[i] = 'sell'
                last_action = 'sell'
        return signals
