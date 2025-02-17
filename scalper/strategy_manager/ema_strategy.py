from collections import deque

from .base_strategy import Strategy
from .indicators import adx, ema, rsi
from .rules import trending_crossover, rsi_overbought_undersold, get_adx_signal


class EmaStrategy(Strategy):
    def __init__(self, short_window: int, long_window: int, rsi_window: int, overbought: float, oversold: float):
        self.short_window = short_window
        self.long_window = long_window
        self.rsi_window = rsi_window
        self.overbought = overbought
        self.oversold = oversold
        self.last_signal = 'hold'
        self.rolling_prices = deque(maxlen=long_window)
        self.trend_counter = 0
        self.trend_threshold = 0

    def generate_signal(self, price: float) -> dict:
        ''' Roll prices and compute signal based on SMA, EMA, and RSI. '''
        self.rolling_prices.append(price)
        if len(self.rolling_prices) < self.long_window:
            return {'signal': 'hold', 'short_sma': None, 'long_sma': None, 'rsi': None}
        return self.__compute_signal()

    def __compute_signal(self) -> dict:
        ''' Calculate MAs/RSI and generate signal based on trending crossovers and RSI. '''
        short_sma = ema(self.rolling_prices, self.short_window)
        long_sma = ema(self.rolling_prices, self.long_window)
        rsi_value = rsi(self.rolling_prices, self.rsi_window)
        adx_results = adx(self.rolling_prices, self.rsi_window)
        adx_value, plus_di, minus_di = adx_results['adx'], adx_results['+di'], adx_results['-di']

        sma_signal, sma_last_signal, self.trend_counter = trending_crossover(
            short_sma, long_sma, self.last_signal, self.trend_counter, self.trend_threshold)
        rsi_signal = rsi_overbought_undersold(rsi_value, self.overbought, self.oversold)
        adx_signal = get_adx_signal(adx_value, plus_di, minus_di)

        if sma_signal == rsi_signal == adx_signal:
            signal = sma_signal
            self.last_signal = sma_last_signal
        else:
            signal = 'hold'

        return {'signal': signal, 'short_sma': short_sma, 'long_sma': long_sma, 'rsi': rsi_value}
