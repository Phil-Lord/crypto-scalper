import pandas as pd
import numpy as np

from .base_strategy import Strategy
from strategy_manager.indicators import AdxIndicator, EmaIndicator, RsiIndicator
from strategy_manager.rules import AdxThresholdRule, MaCrossoverRule, RsiThresholdRule


class PrecisionTrendStrategy(Strategy):
    ''' EMA crossover, RSI, ADX, ATR '''

    def __init__(self, short_ema: int, long_ema: int, rsi_window: int, rsi_oversold: float,
                 rsi_overbought: float, adx_window: int, adx_threshold: int,
                 weight_crossover: float, weight_rsi: float, weight_adx: float,
                 buy_threshold: float, sell_threshold: float):
        super().__init__()
        total_weight = weight_crossover + weight_rsi
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

        self.register_indicator('short_ema', EmaIndicator(short_ema))
        self.register_indicator('long_ema', EmaIndicator(long_ema))
        self.register_rule('crossover', MaCrossoverRule('short_ema', 'long_ema'))
        self.weight_crossover = weight_crossover / total_weight

        self.register_indicator('rsi', RsiIndicator(rsi_window))
        self.register_rule('rsi_threshold', RsiThresholdRule('rsi', rsi_oversold, rsi_overbought))
        self.weight_rsi = weight_rsi / total_weight

        self.register_indicator('adx', AdxIndicator(adx_window))
        self.register_rule('adx_threshold', AdxThresholdRule('adx', adx_threshold))
        self.weight_adx = weight_adx / total_weight

    def _generate_signal(self, rule_results: dict) -> str:
        crossover_signal = rule_results['crossover']
        rsi_threshold_signal = rule_results['rsi_threshold']
        adx_threshold_signal = rule_results['adx_threshold']

        signal_map = {'buy': 1, 'hold': 0, 'sell': -1}
        score = (self.weight_crossover * signal_map[crossover_signal] +
                 self.weight_rsi * signal_map[rsi_threshold_signal] +
                 self.weight_adx * signal_map[adx_threshold_signal])

        if score > self.buy_threshold:
            return 'buy'
        elif score < self.sell_threshold:
            return 'sell'
        else:
            return 'hold'

    def _generate_signals(self, results: pd.DataFrame) -> pd.DataFrame:
        signal_map = {'buy': 1, 'hold': 0, 'sell': -1}
        indicators = {
            'crossover': self.weight_crossover,
            'rsi_threshold': self.weight_rsi,
            'adx_threshold': self.weight_adx
        }
        total_scores = sum(
            results[indicator].map(signal_map) * weight
            for indicator, weight in indicators.items()
        )

        conditions = [total_scores > self.buy_threshold, total_scores < self.sell_threshold]
        choices = ['buy', 'sell']
        return np.select(conditions, choices, default='hold')
