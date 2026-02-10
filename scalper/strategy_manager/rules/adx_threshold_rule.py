import numpy as np
import pandas as pd

from data_system import Signal

from .base_rule import Rule


class AdxThresholdRule(Rule):
    def __init__(self, adx_name: str, threshold: float):
        self.adx_name = adx_name
        self.threshold = threshold

    def check(self, current_state: dict) -> Signal:
        adx = current_state[self.adx_name]
        if adx is None:
            return Signal.HOLD
        return Signal.BUY if adx >= self.threshold else Signal.HOLD

    def compute_vectorised(self, results: pd.DataFrame) -> pd.Series:
        return np.where(results[self.adx_name] >= self.threshold, 'buy', 'hold')
