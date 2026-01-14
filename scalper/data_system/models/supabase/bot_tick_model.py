from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID


class Signal(str, Enum):
    BUY = 'buy'
    HOLD = 'hold'
    SELL = 'sell'


@dataclass(frozen=True)
class BotTick:
    '''
    Dataclass representing a single tick of bot activity.

    Attributes:
        bot_id (str): Identifier of the bot associated with this tick, e.g., `btc_1m_001`.
        run_id (UUID): Identifier of the bot run associated with this tick.

        timestamp (datetime): Heartbeat time - the moment the bot woke up to check the interval.

        balance_base (Decimal): Balance of the base currency at this tick, hit API on buy/sell.
        balance_quote (Decimal): Balance of the quote currency at this tick, hit API on buy/sell.

        price (Decimal): Price of the trading pair at this tick.
        signal (Signal): Trading signal generated at this tick.

        order_executed (bool): Whether an order was executed at this tick.
        executed_at (Optional[datetime]): Timestamp when the order was executed, if applicable.
        execution_price (Optional[Decimal]): Price at which the order was executed, if applicable.
        execution_volume (Optional[float]): Volume of the order executed, if applicable.
        execution_fee (Optional[Decimal]): Fee paid for the order, if applicable.

        error (Optional[str]): Error message if any issue occurred during this tick.

        id (Optional[int]): Primary key for database storage, none if not yet saved.
    '''
    # Identifiers
    bot_id: str
    run_id: UUID

    # Time series data
    timestamp: datetime

    # Post-interval portfolio state
    balance_base: Decimal
    balance_quote: Decimal

    # Market state
    price: Decimal
    signal: Signal

    # Order execution details (if applicable)
    order_executed: bool = False
    executed_at: datetime | None = None
    execution_price: Decimal | None = None
    execution_volume: float | None = None
    execution_fee: Decimal | None = None

    # Error information
    error: str | None = None

    # Database primary key
    id: int | None = None
