import pandas as pd

from .base_indicator import Indicator


class SmaIndicator(Indicator):
    def __init__(self, window: int):
        self.window = window
        self.prices = []

    def update(self, price: float) -> float:
        self.prices.append(price)
        if len(self.prices) < self.window:
            return None
        return sum(self.prices[-self.window:]) / self.window

    def compute_vectorised(self, prices: pd.Series) -> pd.Series:
        return prices.rolling(self.window).mean()
