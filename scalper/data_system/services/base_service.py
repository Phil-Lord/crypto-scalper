from abc import ABC, abstractmethod

import pandas as pd


class Service(ABC):
    @abstractmethod
    def __init__(self, client) -> None:
        ''' Sets the client for the service. '''
        pass

    @abstractmethod
    def add(self, *args, **kwargs) -> None:
        ''' Inserts data based on the provided arguments. '''
        pass

    @abstractmethod
    def get(self, *args, **kwargs) -> pd.DataFrame:
        ''' Gets data based on the provided arguments. '''
        pass
