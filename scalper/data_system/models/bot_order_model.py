from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


class Side(str, Enum):
    BUY = 'buy'
    SELL = 'sell'


class OrderStatus(str, Enum):
    PLACED = 'placed'
    FILLED = 'filled'
    FAILED = 'failed'


@dataclass(frozen=True)
class BotOrder:
    '''
    Dataclass representing a single order placed by a bot.

    Attributes:
        id (UUID): Unique order identifier.
        bot_id (str): Identifier of the bot which placed the order, e.g., `btc_1m_001`.
        run_id (UUID): Identifier of the bot run associated with the order.
        tick_id (int | None): Identifier of the bot tick associated with the order.

        txid (str): Order ID returned by the exchange when the order was placed.
        side (Side): Side of the order (buy/sell).
        status (OrderStatus): Status of the order (defaults to `placed`).
        placed_at (datetime): Timestamp when the order was placed (defaults to current time).

        filled_at (datetime | None): Timestamp when the order was filled.
        price (Decimal | None): Average price at which the order was executed.
        volume (Decimal | None): Order volume.
        fee (Decimal | None): Fee paid.
    '''
    bot_id: str
    run_id: UUID

    txid: str
    side: Side
    status: OrderStatus = OrderStatus.PLACED
    placed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    filled_at: datetime | None = None
    price: Decimal | None = None
    volume: Decimal | None = None
    fee: Decimal | None = None

    id: UUID = field(default_factory=uuid4)
    tick_id: int | None = None
