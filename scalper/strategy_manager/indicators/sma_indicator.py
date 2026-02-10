import pandas as pd

from .base_indicator import Indicator


class SmaIndicator(Indicator):
    def __init__(self, window: int):
        self.window = window
        self.prices = []

    def update(self, ohlc: pd.Series) -> float | None:
        self.prices.append(ohlc['price'])
        if len(self.prices) < self.window:
            return None
        return sum(self.prices[-self.window:]) / self.window

    def compute_vectorised(self, ohlc: pd.DataFrame) -> pd.Series:
        return ohlc['price'].rolling(self.window).mean()
