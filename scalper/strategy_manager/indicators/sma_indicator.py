from collections import deque

import pandas as pd

from .base_indicator import Indicator


class SmaIndicator(Indicator):
    def __init__(self, window: int):
        self.window = window
        self.prices = deque(maxlen=window)

    def update(self, ohlc: pd.Series) -> float | None:
        self.prices.append(ohlc['close'])
        if len(self.prices) < self.window:
            return None
        return sum(self.prices) / self.window

    def compute_vectorised(self, ohlc: pd.DataFrame) -> pd.Series:
        return ohlc['close'].rolling(self.window).mean()

    def reset(self) -> None:
        self.prices = deque(maxlen=self.window)
