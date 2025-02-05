from abc import ABC, abstractmethod


class Strategy(ABC):
    @abstractmethod
    def evaluate(self, price: float) -> str:
        '''
        Returns a 'buy', 'sell', or 'hold' signal based on the passed price.
        '''
        pass
