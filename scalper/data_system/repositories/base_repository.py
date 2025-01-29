from abc import ABC, abstractmethod


class Repository(ABC):
    @abstractmethod
    def add(self, *args, **kwargs):
        '''
        Insert data based on the provided arguments.
        '''
        pass

    @abstractmethod
    def get(self, *args, **kwargs):
        '''
        Get data based on the provided arguments.
        '''
        pass
