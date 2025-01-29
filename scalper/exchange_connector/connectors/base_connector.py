from abc import ABC, abstractmethod


class Connector(ABC):
    @abstractmethod
    def fetch(self, *args, **kwargs):
        '''
        Fetch data based on the provided arguments.
        '''
        pass
