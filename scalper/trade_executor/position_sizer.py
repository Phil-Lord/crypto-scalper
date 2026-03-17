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
        symbol_base (str): Symbol of the base asset, e.g., 'XBT'.
        symbol_quote (str): Symbol of the quote asset, e.g., 'GBP'.
        balance_base (Decimal): Balance of the base asset.
        balance_quote (Decimal): Balance of the quote asset.
    '''
    symbol_base: str
    symbol_quote: str
    balance_base: Decimal
    balance_quote: Decimal


class PositionSizer(ABC):
    @abstractmethod
    def calculate_volume(self, signal: Signal, balances: PairBalances) -> Decimal:
        ''' Calculates the order volume based on the provided signal and current balances.'''
        pass


class AllInPositionSizer(PositionSizer):
    def calculate_volume(self, signal: Signal, balances: PairBalances) -> Decimal:
        ''' Allocates the entire available balance to the trade. '''
        if signal == Signal.BUY:
            return balances.balance_quote
        elif signal == Signal.SELL:
            return balances.balance_base
        raise ValueError(f'Cannot calculate volume for signal: {signal}')
