from abc import ABC, abstractmethod

import pandas as pd


class Rule(ABC):
    @abstractmethod
    def check(self, current_state: dict[str, any]) -> str:
        ''' Check rule against current state during live trading. '''
        pass

    @abstractmethod
    def compute_vectorised(self, results: pd.DataFrame) -> pd.Series:
        ''' Compute rule signals across the results dataframe for backtesting. '''
        pass
