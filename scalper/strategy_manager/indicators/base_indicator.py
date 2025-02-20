from abc import ABC, abstractmethod

import pandas as pd


class Indicator(ABC):
    @abstractmethod
    def update(self, price: float) -> any:
        """ Update indicator with new price for live trading. """
        pass

    @abstractmethod
    def compute_vectorised(self, prices: pd.Series) -> pd.Series:
        """ Compute indicator for entire series during backtesting. """
        pass
