import pandas as pd

from .base_strategy import Strategy
from strategy_manager.indicators import SmaIndicator
from strategy_manager.rules import MaCrossoverRule


class SmaStrategy(Strategy):
    def __init__(self, short_window: int, long_window: int):
        super().__init__()
        self.register_indicator('short_sma', SmaIndicator(short_window))
        self.register_indicator('long_sma', SmaIndicator(long_window))
        self.register_rule('crossover', MaCrossoverRule('short_sma', 'long_sma'))

    def _generate_signal(self, rule_results: dict) -> str:
        return rule_results['crossover']

    def _generate_signals(self, results: pd.DataFrame) -> pd.DataFrame:
        results['signal'] = results['crossover']
        return results
