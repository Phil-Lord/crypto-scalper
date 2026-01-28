from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Bot:
    '''
    Dataclass representing a trading bot configuration.

    Attributes:
        id (str): Human-readable unique identifier for the bot, e.g., `btc_1m_001`.
        pair (str): Trading pair in Kraken format, e.g., `XXBTZGBP`.
        strategy_name (str): Name of the trading strategy, e.g., `PrecisionTrendStrategy`.
        strategy_version (str): Version of the trading strategy, e.g., `v1.0.0`.
        interval (int): Time interval in minutes for the bot's operation.
        parameters (dict[str, Any]): JSON-serialisable dictionary of strategy parameters.
        created_at (datetime): Timestamp of bot creation, defaults to current UTC time.
    '''
    id: str
    pair: str
    strategy_name: str
    strategy_version: str
    interval: int
    parameters: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
