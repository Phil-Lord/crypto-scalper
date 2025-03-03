from collections import deque

from .base_strategy_legacy import StrategyLegacy
from .indicators import sma
from .rules import crossover


class SmaStrategyLegacy(StrategyLegacy):
    def __init__(self, short_window: int, long_window: int):
        self.short_window = short_window
        self.long_window = long_window
        self.last_signal = 'hold'
        self.rolling_prices = deque(maxlen=long_window)

    def generate_signal(self, price: float) -> dict:
        ''' Roll prices and compute signal based on SMA. '''
        self.rolling_prices.append(price)
        if len(self.rolling_prices) < self.long_window:
            return {'signal': 'hold', 'short_sma': None, 'long_sma': None}
        return self.__compute_signal()

    def __compute_signal(self) -> dict:
        ''' Calculate SMAs and generate signal based on the Golden or Death Cross. '''
        short_sma = sma(self.rolling_prices, self.short_window)
        long_sma = sma(self.rolling_prices, self.long_window)
        signal, self.last_signal = crossover(short_sma, long_sma, self.last_signal)
        return {'signal': signal, 'short_sma': short_sma, 'long_sma': long_sma}
