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
        delta = prices.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain_wilder = pd.Series(index=prices.index, dtype=float)
        avg_loss_wilder = pd.Series(index=prices.index, dtype=float)

        # Manually compute the initial average gain/loss over the first `window` deltas.
        initial_gains = gain.iloc[1:self.window]  # skip NaN at index 0.
        initial_losses = loss.iloc[1:self.window]

        avg_gain = initial_gains.mean()
        avg_loss = initial_losses.mean()

        avg_gain_wilder.iloc[self.window] = avg_gain
        avg_loss_wilder.iloc[self.window] = avg_loss

        # Now apply Wilder smoothing from self.window + 1 onwards
        for i in range(self.window + 1, len(prices)):
            avg_gain = ((avg_gain * (self.window - 1)) + gain.iloc[i]) / self.window
            avg_loss = ((avg_loss * (self.window - 1)) + loss.iloc[i]) / self.window
            avg_gain_wilder.iloc[i] = avg_gain
            avg_loss_wilder.iloc[i] = avg_loss

        rs = avg_gain_wilder / avg_loss_wilder
        rsi = 100 - (100 / (1 + rs))
        return rsi
