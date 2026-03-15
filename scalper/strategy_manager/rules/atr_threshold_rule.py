import numpy as np
import pandas as pd

from data_system import Signal

from .base_rule import Rule


class AtrThresholdRule(Rule):
    def __init__(self, atr_name: str, threshold: float):
        self.atr_name = atr_name
        self.threshold = threshold

    def check(self, current_state: dict) -> Signal:
        atr_ratio = current_state.get(self.atr_name)
        if atr_ratio is None:
            return Signal.HOLD
        return Signal.BUY if atr_ratio >= self.threshold else Signal.HOLD

    def compute_vectorised(self, results: pd.DataFrame) -> pd.Series:
        return pd.Series(np.where(results[self.atr_name] >= self.threshold, 'buy', 'hold'), index=results.index, dtype=object)
