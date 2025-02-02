from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    def __init__(self):
        # The results of a run for analysis.
        self.results = pd.DataFrame()

    @abstractmethod
    def evaluate(self, price: float) -> str:
        '''
        Returns a 'buy', 'sell', or 'hold' signal based on the passed price.
        '''
        pass

    def get_results(self) -> pd.DataFrame:
        '''
        Returns the results DataFrame prepared by the strategy throughout its run.
        '''
        return self.results
