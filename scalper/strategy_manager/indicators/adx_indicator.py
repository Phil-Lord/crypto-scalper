import numpy as np
import pandas as pd

from .base_indicator import Indicator


class AdxIndicator(Indicator):
    def __init__(self, window: int):
        self.window = window
        self.prev_high = None
        self.prev_low = None
        self.prev_close = None

        self.smoothed_tr = None
        self.smoothed_plus_dm = None
        self.smoothed_minus_dm = None
        self.adx = None

    def update(self, ohlc: pd.Series) -> float:
        high = ohlc['high']
        low = ohlc['low']
        close = ohlc['price']  # Assuming 'price' is close

        if self.prev_high is None:
            # First update: cannot compute anything yet
            self.prev_high, self.prev_low, self.prev_close = high, low, close
            return None

        # Calculate directional movements
        up_move = high - self.prev_high
        down_move = self.prev_low - low

        plus_dm = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm = down_move if (down_move > up_move and down_move > 0) else 0.0

        # True range calculation
        tr = max(high - low, abs(high - self.prev_close), abs(low - self.prev_close))

        alpha = 1 / self.window

        # Wilder's smoothing (EMA)
        self.smoothed_tr = tr if self.smoothed_tr is None else (
            1 - alpha) * self.smoothed_tr + alpha * tr
        self.smoothed_plus_dm = plus_dm if self.smoothed_plus_dm is None else (
            1 - alpha) * self.smoothed_plus_dm + alpha * plus_dm
        self.smoothed_minus_dm = minus_dm if self.smoothed_minus_dm is None else (
            1 - alpha) * self.smoothed_minus_dm + alpha * minus_dm

        plus_di = 100 * self.smoothed_plus_dm / self.smoothed_tr if self.smoothed_tr != 0 else 0
        minus_di = 100 * self.smoothed_minus_dm / self.smoothed_tr if self.smoothed_tr != 0 else 0

        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * \
            100 if (plus_di + minus_di) != 0 else 0
        self.adx = dx if self.adx is None else (1 - alpha) * self.adx + alpha * dx

        # Update previous values
        self.prev_high, self.prev_low, self.prev_close = high, low, close
        return self.adx

    def compute_vectorised(self, ohlc: pd.DataFrame) -> pd.Series:
        highs = ohlc['high']
        lows = ohlc['low']
        closes = ohlc['price']

        # Directional Movement
        up_move = highs.diff()
        down_move = lows.diff()

        plus_dm = pd.Series(np.where((up_move > down_move) & (
            up_move > 0), up_move, 0.0), index=ohlc.index)
        minus_dm = pd.Series(np.where((down_move > up_move) & (
            down_move > 0), down_move, 0.0), index=ohlc.index)

        # True Range
        tr1 = highs - lows
        tr2 = abs(highs - closes.shift())
        tr3 = abs(lows - closes.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        alpha = 1 / self.window

        # Do NOT set first value to np.nan; let ewm use the first valid value as seed
        smoothed_tr = tr.ewm(alpha=alpha, adjust=False).mean()
        smoothed_plus_dm = plus_dm.ewm(alpha=alpha, adjust=False).mean()
        smoothed_minus_dm = minus_dm.ewm(alpha=alpha, adjust=False).mean()

        plus_di = 100 * smoothed_plus_dm / smoothed_tr
        minus_di = 100 * smoothed_minus_dm / smoothed_tr

        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)
              ).replace([np.inf, -np.inf], 0).fillna(0) * 100

        adx = dx.ewm(alpha=alpha, adjust=False).mean()

        return adx.rename('adx')
