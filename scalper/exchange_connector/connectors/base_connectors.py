from abc import ABC, abstractmethod


class FetchConnector(ABC):
    @abstractmethod
    def fetch(self, *args, **kwargs):
        '''
        Fetch data based on the provided arguments.
        '''
        pass


class PlaceConnector(ABC):
    @abstractmethod
    def place(self, *args, **kwargs):
        '''
        Place an order based on the provided arguments.
        '''
        pass
