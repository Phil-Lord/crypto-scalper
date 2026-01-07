from abc import ABC, abstractmethod


class TradeRepository(ABC):
    @abstractmethod
    def add(self, raw_trades: list[list[any]]) -> None:
        '''
        Inserts a list of trades for a certain pair in their raw format from the Kraken API.

        :param raw_trades: List of trade lists, e.g. [[price, vol, time, b/s, m/l, misc, id], ...].
        :param pair: Trading pair identifier, e.g. 'XXBTZGBP'.
        '''
        pass

    @abstractmethod
    def get(self, pair: str, start: int = None, end: int = None) -> list[dict]:
        '''
        Fetches trades for a certain pair between a start and end date.

        :param pair: Trading pair identifier, e.g. 'XXBTZGBP'.
        :param start: Start timestamp. If None, fetches from the earliest trade.
        :param end: End timestamp. If None, fetches up to the latest trade.

        :return: Trades Dataframe.
        '''
        pass
