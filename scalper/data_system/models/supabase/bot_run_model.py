from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


@dataclass(frozen=True)
class BotRun:
    '''
    Dataclass representing a single run of a trading bot.

    Attributes:
        id (UUID): Unique identifier for the bot run.
        bot_id (str): Identifier of the bot associated with this run.
        started_at (datetime): Timestamp when the bot run started, defaults to current UTC time.
        completed_at (datetime): Timestamp when the bot run ended, if applicable.
    '''
    id: UUID
    bot_id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
