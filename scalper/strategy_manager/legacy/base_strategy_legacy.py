from abc import ABC, abstractmethod


class StrategyLegacy(ABC):
    @abstractmethod
    def generate_signal(self, price: float) -> dict:
        ''' Returns a 'buy', 'sell', or 'hold' signal based on the passed price. '''
        pass
