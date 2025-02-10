from .base_strategy import Strategy
from .ema_strategy import EmaStrategy
from .sma_strategy import SmaStrategy


class StrategyManager:
    def __init__(self):
        self.strategies = {
            'sma': SmaStrategy,
            'ema': EmaStrategy
        }

    def get_strategy(self, strategy_name: str, **kwargs) -> Strategy:
        if strategy_name not in self.strategies:
            raise ValueError(f'Strategy {strategy_name} does not exist.')
        return self.strategies[strategy_name](**kwargs)
