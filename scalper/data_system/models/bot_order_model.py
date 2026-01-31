from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


class Side(str, Enum):
    BUY = 'buy'
    SELL = 'sell'


@dataclass(frozen=True)
class BotOrder:
    '''
    Dataclass representing a single order placed by a bot.

    Attributes:
        bot_id (str): Identifier of the bot which placed the order, e.g., `btc_1m_001`.
        run_id (UUID): Identifier of the bot run associated with the order.
        tick_id (int): Identifier of the bot tick associated with the order.

        side (Side): Side of the order (buy/sell).
        price (Decimal): Price at which the order was executed.
        volume (Decimal): Order volume.
        fee (Decimal): Fee paid.
        executed_at (datetime): Timestamp when the order was executed.

        id (UUID): Unique order identifier.
    '''
    bot_id: str
    run_id: UUID
    tick_id: int

    side: Side
    price: Decimal
    volume: Decimal
    fee: Decimal
    executed_at: datetime

    id: UUID = field(default_factory=uuid4)
