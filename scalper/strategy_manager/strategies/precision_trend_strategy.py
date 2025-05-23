import pandas as pd

from .base_strategy import Strategy
from strategy_manager.indicators import EmaIndicator
from strategy_manager.rules import MaCrossoverRule


class PrecisionTrendStrategy(Strategy):
    def __init__(self, short_ema: int, long_ema: int):
        super().__init__()
        self.register_indicator('short_ema', EmaIndicator(short_ema))
        self.register_indicator('long_ema', EmaIndicator(long_ema))
        self.register_rule('crossover', MaCrossoverRule('short_ema', 'long_ema'))

    def _generate_signal(self, rule_results: dict) -> str:
        return rule_results['crossover']

    def _generate_signals(self, results: pd.DataFrame) -> pd.DataFrame:
        return results['crossover']
