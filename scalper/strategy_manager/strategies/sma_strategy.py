import pandas as pd

from data_system import Signal

from .base_strategy import Strategy
from .sma_strategy_config import SmaStrategyConfig
from strategy_manager.indicators import SmaIndicator
from strategy_manager.rules import MaCrossoverRule


class SmaStrategy(Strategy):
    def __init__(self, config: SmaStrategyConfig):
        super().__init__()
        self.config = config
        self.register_indicator('short_sma', SmaIndicator(config.short_window))
        self.register_indicator('long_sma', SmaIndicator(config.long_window))
        self.register_rule('crossover', MaCrossoverRule('short_sma', 'long_sma'))

    def _generate_signal(self, rule_results: dict) -> Signal:
        return rule_results['crossover']

    def _generate_signals(self, results: pd.DataFrame) -> pd.Series:
        return results['crossover']
