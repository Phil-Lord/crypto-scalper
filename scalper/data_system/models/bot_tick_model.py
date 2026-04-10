from dataclasses import dataclass, field
from datetime import datetime, timezone
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
        price (Decimal): Price of the trading pair at this tick.
        signal (Signal): Trading signal generated at this tick.

        balance_base (Decimal): Balance of the base currency at this tick, hit API on buy/sell.
        balance_quote (Decimal): Balance of the quote currency at this tick, hit API on buy/sell.

        error (str | None): Error message if any issue occurred during this tick.

        id (int | None): Primary key for database storage, none if not yet saved.
    '''
    # Identifiers
    bot_id: str
    run_id: UUID

    # Tick data
    price: Decimal
    signal: Signal

    # Post-interval portfolio state
    balance_base: Decimal
    balance_quote: Decimal

    # Auto-set fields
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None
    id: int | None = None
