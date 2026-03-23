from dataclasses import dataclass


@dataclass(frozen=True)
class OhlcCandle:
    '''
    Dataclass representing a single OHLC (Open-High-Low-Close) candle for a trading pair.

    Attributes:
        timestamp (int): Unix timestamp of the candle's start time.
        open (float): Opening price of the candle.
        high (float): Highest price during the candle interval.
        low (float): Lowest price during the candle interval.
        close (float): Closing price of the candle.
        vwap (float): Volume-weighted average price during the candle interval.
        volume (float): Total trading volume during the candle interval.
        count (int): Number of trades during the candle interval.
    '''
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    vwap: float
    volume: float
    count: int
