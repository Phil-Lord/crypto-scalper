import pandas as pd

from .base_indicator import Indicator


class AtrIndicator(Indicator):
    def __init__(self, window: int):
        self.window = window
        self.prev_close = None
        self.smoothed_tr = None

    def update(self, ohlc: pd.Series) -> float:
        high = ohlc['high']
        low = ohlc['low']
        close = ohlc['price']

        if self.prev_close is None:
            self.prev_close = close
            return None

        tr = max(high - low, abs(high - self.prev_close), abs(low - self.prev_close))

        alpha = 1 / self.window
        self.smoothed_tr = tr if self.smoothed_tr is None else (
            1 - alpha) * self.smoothed_tr + alpha * tr

        self.prev_close = close
        return self.smoothed_tr

    def compute_vectorised(self, ohlc: pd.DataFrame) -> pd.Series:
        highs = ohlc['high']
        lows = ohlc['low']
        closes = ohlc['price']

        tr1 = highs - lows
        tr2 = (highs - closes.shift()).abs()
        tr3 = (lows - closes.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        alpha = 1 / self.window
        atr = tr.ewm(alpha=alpha, adjust=False).mean()
        atr.name = 'atr'

        return atr
