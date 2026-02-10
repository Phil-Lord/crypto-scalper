from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from data_system import Signal


class Rule(ABC):
    @abstractmethod
    def check(self, current_state: dict[str, Any]) -> Signal:
        ''' Check rule against current state during live trading. '''
        pass

    @abstractmethod
    def compute_vectorised(self, results: pd.DataFrame) -> pd.Series:
        ''' Compute rule signals across the results dataframe for backtesting. '''
        pass
