import numpy as np
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

        if rsi > self.oversold and prev_rsi <= self.oversold:
            return 'buy'
        elif rsi < self.overbought and prev_rsi >= self.overbought:
            return 'sell'
        return 'hold'

    def compute_vectorised(self, results: pd.DataFrame) -> pd.Series:
        rsi = results[self.rsi_name]
        cross_above_oversold = (rsi > self.oversold) & (rsi.shift(1) <= self.oversold)
        cross_below_overbought = (rsi < self.overbought) & (rsi.shift(1) >= self.overbought)

        signals = np.full(len(results), 'hold', dtype=object)
        signals[cross_above_oversold] = 'buy'
        signals[cross_below_overbought] = 'sell'
        return pd.Series(signals, index=results.index)
