from abc import ABC, abstractmethod
from typing import Any


class FetchConnector(ABC):
    '''
    Abstract base class for connectors that fetch data from the exchange.

    Subclasses implement fetch() for specific data types (trades, ticker, etc.).
    '''

    @abstractmethod
    def fetch(self, *args, **kwargs) -> Any:
        '''
        Fetch data from the exchange.

        :return: Data from the exchange API.
        '''
        pass


class PlaceConnector(ABC):
    '''
    Abstract base class for connectors that place orders on the exchange.

    Subclasses implement place() for specific order types.
    '''

    @abstractmethod
    def place(self, *args, **kwargs) -> Any:
        '''
        Place an order on the exchange.

        :return: Order result from the exchange API.
        '''
        pass
