import pandas as pd

from .base_indicator import Indicator


class EmaIndicator(Indicator):
    def __init__(self, window: int):
        self.window = window
        self.ema = None
        self.alpha = 2 / (window + 1)

    def update(self, price: float) -> float:
        if self.ema is None:
            self.ema = price  # Initialize EMA with the first price.
        else:
            self.ema = (price - self.ema) * self.alpha + self.ema
        return self.ema

    def compute_vectorised(self, prices: pd.Series) -> pd.Series:
        return prices.ewm(self.window, adjust=False).mean()
