from abc import ABC, abstractmethod

from data_system.models import Trade


class TradeRepository(ABC):
    @abstractmethod
    def add(self, trades: list[Trade]) -> None:
        '''
        Inserts a list of trades into the database.

        :param trades: List of Trade domain objects to persist.
        '''
        pass

    @abstractmethod
    def get(self, pair: str, start: float = None, end: float = None) -> list[Trade]:
        '''
        Fetches trades for a trading pair within a time range.

        :param pair: Trading pair identifier, e.g., 'XXBTZGBP'.
        :param start: Start timestamp (Unix seconds). If None, fetches from earliest.
        :param end: End timestamp (Unix seconds). If None, fetches up to latest.
        :return: List of Trade domain objects.
        '''
        pass
