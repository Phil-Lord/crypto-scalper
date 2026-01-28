from dataclasses import dataclass


@dataclass(frozen=True)
class Trade:
    '''
    Dataclass representing a single trade from the exchange.

    This model stores historical trade data fetched from the Kraken API,
    used primarily for backtesting.

    Attributes:
        trade_id (int): Unique trade identifier from the exchange (BIGINT in DB).
        pair (str): Trading pair identifier, e.g., 'XXBTZGBP' (max 15 chars).
        price (float): Trade execution price.
        volume (float): Trade volume.
        timestamp (float): Unix timestamp with sub-second precision.
        side (str): Trade side - 'b' for buy, 's' for sell (1 char).
        order_type (str): Order type - 'm' for market, 'l' for limit (1 char).

    Database Mapping:
        - trade_id: BIGINT (handles high trade volumes)
        - pair: TEXT
        - price: FLOAT
        - volume: FLOAT
        - timestamp: FLOAT (sub-second precision for same-second trades)
        - side: TEXT
        - order_type: TEXT

    Note:
        Primary key is composite (trade_id, pair) since trade IDs are only
        unique per trading pair on Kraken.
    '''
    trade_id: int
    pair: str
    price: float
    volume: float
    timestamp: float
    side: str
    order_type: str
