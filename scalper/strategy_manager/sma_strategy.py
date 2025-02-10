from collections import deque

from .base_strategy import Strategy
from .indicators import sma
from .rules import golden_cross


class SmaStrategy(Strategy):
    def __init__(self, short_window: int, long_window: int):
        self.short_window = short_window
        self.long_window = long_window
        self.last_signal = 'hold'
        self.rolling_prices = deque(maxlen=long_window)

    def generate_signal(self, price: float) -> dict:
        ''' Roll prices and compute signal based on SMA. '''
        self.__roll_prices(price)
        if len(self.rolling_prices) < self.long_window:
            return {'signal': 'hold', 'short_sma': None, 'long_sma': None}
        return self.__compute_signal()

    def __roll_prices(self, price: float) -> None:
        self.rolling_prices.append(price)

    def __compute_signal(self) -> dict:
        ''' Calculate SMAs and generate signal based on the Golden or Death Cross. '''
        short_sma = sma(self.rolling_prices, self.short_window)
        long_sma = sma(self.rolling_prices, self.long_window)
        signal, self.last_signal = golden_cross(short_sma, long_sma, self.last_signal)
        return {'signal': signal, 'short_sma': short_sma, 'long_sma': long_sma}
