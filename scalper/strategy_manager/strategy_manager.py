from .legacy import SmaStrategyLegacy, EmaStrategyLegacy
from .strategies import Strategy, SmaStrategy


class StrategyManager:
    def __init__(self):
        self.strategies = {
            'sma': SmaStrategy,
            'sma_legacy': SmaStrategyLegacy,
            'ema_legacy': EmaStrategyLegacy
        }

    def get_strategy(self, strategy_name: str, **kwargs) -> Strategy:
        if strategy_name not in self.strategies:
            raise ValueError(f'Strategy {strategy_name} does not exist.')
        return self.strategies[strategy_name](**kwargs)
