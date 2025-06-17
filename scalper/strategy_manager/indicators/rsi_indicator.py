import numpy as np
import pandas as pd

from .base_indicator import Indicator


class RsiIndicator(Indicator):
    def __init__(self, window: int):
        self.window = window
        self.prices = []
        self.avg_gain, self.avg_loss, self.prev_price = None, None, None

    def update(self, price: float) -> float:
        if self.prev_price is None:
            self.prev_price = price
            return None

        delta = price - self.prev_price
        self.prev_price = price
        gain = max(delta, 0)
        loss = max(-delta, 0)

        if len(self.prices) < self.window:
            self.prices.append(price)
            return None

        if self.avg_gain is None:
            # Calculate initial average gain and loss.
            self.avg_gain = np.mean([max(self.prices[i+1] - self.prices[i], 0)
                                    for i in range(self.window - 1)])
            self.avg_loss = np.mean([max(self.prices[i] - self.prices[i+1], 0)
                                    for i in range(self.window - 1)])
        else:
            self.avg_gain = (self.avg_gain * (self.window - 1) + gain) / self.window
            self.avg_loss = (self.avg_loss * (self.window - 1) + loss) / self.window

        if self.avg_loss == 0:
            return 100  # Max RSI when no losses.

        rs = self.avg_gain / self.avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def compute_vectorised(self, prices: pd.Series) -> pd.Series:
        self.prices = []
        self.avg_gain, self.avg_loss, self.prev_price = None, None, None

        rsi_values = []
        for price in prices:
            rsi = self.update(price)
            rsi_values.append(rsi)

        return pd.Series(rsi_values, index=prices.index, dtype=float)
