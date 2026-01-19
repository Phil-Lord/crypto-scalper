from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class Indicator(ABC):
    @abstractmethod
    def update(self, ohlc: pd.Series) -> Any:
        ''' Update indicator with new ohlc for live trading. '''
        pass

    @abstractmethod
    def compute_vectorised(self, ohlc: pd.DataFrame) -> pd.Series:
        ''' Compute indicator for entire series during backtesting. '''
        pass
