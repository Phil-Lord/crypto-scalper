from abc import ABC, abstractmethod

import pandas as pd


class Indicator(ABC):
    @abstractmethod
    def update(self, ohlc: pd.Series) -> float | None:
        ''' Update indicator with new ohlc for live trading. '''
        pass

    @abstractmethod
    def compute_vectorised(self, ohlc: pd.DataFrame) -> pd.Series:
        ''' Compute indicator for entire series during backtesting. '''
        pass
