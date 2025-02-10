from collections import deque

from .base_strategy import Strategy
from .indicators import ema, rsi, sma
from .rules import golden_cross, rsi_overbought_undersold


class EmaStrategy(Strategy):
    def __init__(self, short_window: int, long_window: int, rsi_window: int, overbought: float, oversold: float):
        self.short_window = short_window
        self.long_window = long_window
        self.rsi_window = rsi_window
        self.overbought = overbought
        self.oversold = oversold
        self.last_signal = 'hold'
        self.rolling_prices = deque(maxlen=long_window)

    def generate_signal(self, price: float) -> dict:
        ''' Roll prices and compute signal based on SMA, EMA, and RSI. '''
        self.__roll_prices(price)
        if len(self.rolling_prices) < self.long_window:
            return {'signal': 'hold', 'short_sma': None, 'long_sma': None, 'rsi': None}
        return self.__compute_signal()

    def __roll_prices(self, price: float) -> None:
        self.rolling_prices.append(price)

    def __compute_signal(self) -> dict:
        ''' Calculate MAs/RSI and generate signal based on the Golden Cross and RSI. '''
        short_sma = ema(self.rolling_prices, self.short_window)
        long_sma = sma(self.rolling_prices, self.long_window)
        rsi_value = rsi(self.rolling_prices, self.rsi_window)

        sma_signal, sma_last_signal = golden_cross(short_sma, long_sma, self.last_signal)
        rsi_signal = rsi_overbought_undersold(rsi_value, self.overbought, self.oversold)

        if sma_signal == rsi_signal:
            signal = sma_signal
            self.last_signal = sma_last_signal
        else:
            signal = 'hold'

        return {'signal': signal, 'short_sma': short_sma, 'long_sma': long_sma, 'rsi': rsi_value}
