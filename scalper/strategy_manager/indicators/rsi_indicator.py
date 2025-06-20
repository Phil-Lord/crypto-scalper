import numpy as np
import pandas as pd

from .base_indicator import Indicator


class RsiIndicator(Indicator):
    def __init__(self, window: int):
        self.window = window
        self.prices = []
        self.avg_gain, self.avg_loss, self.prev_price = None, None, None

    def update(self, ohlc: pd.Series) -> float:
        if self.prev_price is None:
            self.prev_price = ohlc['price']
            return None

        delta = ohlc['price'] - self.prev_price
        self.prev_price = ohlc['price']
        gain = max(delta, 0)
        loss = max(-delta, 0)

        if len(self.prices) < self.window + 1:
            self.prices.append(ohlc['price'])
            return None
        else:
            self.prices = self.prices[-(self.window + 1):]

        if self.avg_gain is None:
            # Calculate initial average gain and loss.
            deltas = np.diff(self.prices[-(self.window + 1):])
            gains = np.maximum(deltas, 0)
            losses = np.maximum(-deltas, 0)
            self.avg_gain = np.mean(gains)
            self.avg_loss = np.mean(losses)
        else:
            self.avg_gain = (self.avg_gain * (self.window - 1) + gain) / self.window
            self.avg_loss = (self.avg_loss * (self.window - 1) + loss) / self.window

        if self.avg_loss == 0:
            return 100  # Max RSI when no losses.

        rs = self.avg_gain / self.avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def compute_vectorised(self, ohlc: pd.DataFrame) -> pd.Series:
        self.prices = []
        self.avg_gain, self.avg_loss, self.prev_price = None, None, None

        rsi_values = []
        for _, row in ohlc.iterrows():
            rsi = self.update(row)
            rsi_values.append(rsi)

        return pd.Series(rsi_values, index=ohlc['price'].index, dtype=float)
