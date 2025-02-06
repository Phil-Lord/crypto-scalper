import pandas as pd

from .base_strategy import Strategy
from .indicators import sma
from .rules import golden_cross


class SmaStrategy(Strategy):
    def __init__(self, short_window: int, long_window: int):
        super().__init__()
        self.short_window = short_window
        self.long_window = long_window
        self.last_signal = 'hold'
        self.rolling_prices = []

    def evaluate(self, price: float) -> dict:
        ''' Roll prices and compute signal based on SMA. '''
        ready_to_evaluate = self.__roll_prices(price)
        if not ready_to_evaluate:
            return {'signal': 'hold', 'short_sma': None, 'long_sma': None}

        return self.__compute_signal()

    def __roll_prices(self, price: float) -> bool:
        ''' Roll prices and return false until we can calculate the long SMA. '''
        self.rolling_prices.append(price)

        if len(self.rolling_prices) > self.long_window:
            self.rolling_prices.pop(0)

        return len(self.rolling_prices) >= self.long_window

    def __compute_signal(self) -> dict:
        ''' Calculate SMAs and generate signal based on the Golden or Death Cross. '''
        short_sma = sma(self.rolling_prices, self.short_window)
        long_sma = sma(self.rolling_prices, self.long_window)

        signal, self.last_signal = golden_cross(short_sma, long_sma, self.last_signal)

        return {'signal': signal, 'short_sma': short_sma, 'long_sma': long_sma}
