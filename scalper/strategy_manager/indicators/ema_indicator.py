import pandas as pd

from .base_indicator import Indicator


class EmaIndicator(Indicator):
    def __init__(self, window: int):
        self.window = window
        self.ema = None
        self.alpha = 2 / (window + 1)

    def update(self, ohlc: pd.Series) -> float | None:
        if self.ema is None:
            self.ema = ohlc['close']  # Initialise EMA with the first price.
        else:
            self.ema = (ohlc['close'] - self.ema) * self.alpha + self.ema
        return self.ema

    def compute_vectorised(self, ohlc: pd.DataFrame) -> pd.Series:
        return ohlc['close'].ewm(span=self.window, adjust=False).mean()

    def reset(self) -> None:
        self.ema = None
