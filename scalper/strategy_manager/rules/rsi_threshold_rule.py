import pandas as pd

from .base_rule import Rule


class RsiThresholdRule(Rule):
    def __init__(self, rsi_name: str, oversold: float, overbought: float):
        self.rsi_name = rsi_name
        self.oversold = oversold
        self.overbought = overbought

    def check(self, current_state: dict) -> str:
        pass

    def compute_vectorised(self, results: pd.DataFrame) -> pd.Series:
        pass
