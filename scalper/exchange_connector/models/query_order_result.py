from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class QueryOrderStatus(str, Enum):
    PENDING = 'pending'
    OPEN = 'open'
    CLOSED = 'closed'
    CANCELED = 'canceled'
    EXPIRED = 'expired'


@dataclass(frozen=True)
class QueryOrderResult:
    '''
    Dataclass representing the execution details of an order queried from the exchange.

    This model transforms the raw Kraken QueryOrders API response into a typed
    domain object, providing a platform-agnostic abstraction for order results.

    Attributes:
        txid (str): Transaction ID for the queried order.
        price (Decimal): Average price at which the order was executed.
        volume (Decimal): Executed volume of the order in the base currency.
        fee (Decimal): Fee charged for the order in the quote currency.
        status (QueryOrderStatus): Status of the order.
    '''
    txid: str
    price: Decimal
    volume: Decimal
    fee: Decimal
    status: QueryOrderStatus
