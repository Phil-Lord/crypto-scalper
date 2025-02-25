from abc import ABC, abstractmethod

import pandas as pd


class Rule(ABC):
    @abstractmethod
    def check(self, current_state: dict[str, any]) -> str:
        ''' Check rule against current state during live trading. '''
        pass

    @abstractmethod
    def compute_vectorised(self, data: pd.DataFrame) -> pd.Series:
        ''' Compute rule signals across dataframe for backtesting. '''
        pass
