from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from data_system import Signal


@dataclass(frozen=True)
class PairBalances:
    '''
    Dataclass representing the balances of a trading pair.
    This merges pair symbol information with balance details.

    Attributes:
        base_symbol (str): Symbol of the base asset, e.g., 'BTC'.
        quote_symbol (str): Symbol of the quote asset, e.g., 'USD'.
        base (Decimal): Balance of the base asset.
        quote (Decimal): Balance of the quote asset.
    '''
    base_symbol: str
    quote_symbol: str
    base: Decimal
    quote: Decimal


class PositionSizer(ABC):
    @abstractmethod
    def calculate_volume(self, signal: Signal, balances: PairBalances) -> Decimal:
        ''' Calculates the order volume based on the provided signal and current balances.'''
        pass
