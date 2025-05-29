import pandas as pd

from .base_strategy import Strategy
from strategy_manager.indicators import EmaIndicator, RsiIndicator
from strategy_manager.rules import MaCrossoverRule, RsiThresholdRule


class PrecisionTrendStrategy(Strategy):
    def __init__(self, short_ema: int, long_ema: int, rsi_window: int, rsi_oversold: float, rsi_overbought: float, weight_crossover: float, weight_rsi: float):
        super().__init__()
        total_weight = weight_crossover + weight_rsi
        self.weight_crossover = weight_crossover / total_weight
        self.weight_rsi = weight_rsi / total_weight

        self.register_indicator('short_ema', EmaIndicator(short_ema))
        self.register_indicator('long_ema', EmaIndicator(long_ema))
        self.register_rule('crossover', MaCrossoverRule('short_ema', 'long_ema'))

        self.register_indicator('rsi', RsiIndicator(rsi_window))
        self.register_rule('rsi_threshold', RsiThresholdRule('rsi', rsi_oversold, rsi_overbought))

    def _generate_signal(self, rule_results: dict) -> str:
        crossover_signal = rule_results['crossover']
        rsi_threshold_signal = rule_results['rsi_threshold']

        signal_map = {'buy': 1, 'hold': 0, 'sell': -1}
        score = (self.weight_crossover * signal_map[crossover_signal] +
                 self.weight_rsi * signal_map[rsi_threshold_signal])

        if score > 0.5:
            return 'buy'
        elif score < -0.5:
            return 'sell'
        else:
            return 'hold'

    def _generate_signals(self, results: pd.DataFrame) -> pd.DataFrame:
        signal_map = {'buy': 1, 'hold': 0, 'sell': -1}
        crossover_scores = results['crossover'].map(signal_map)
        rsi_scores = results['rsi_threshold'].map(signal_map)

        total_scores = (self.weight_crossover * crossover_scores +
                        self.weight_rsi * rsi_scores)

        conditions = [total_scores > 0.5, total_scores < -0.5]
        choices = ['buy', 'sell']
        return pd.Series(
            pd.cut(total_scores, [-float('inf'), -0.5, 0.5, float('inf')], labels=['sell', 'hold', 'buy']))
