from .base_connectors import FetchConnector
from exchange_connector.api import KrakenApiClient
from exchange_connector.models import OhlcCandle
from exchange_connector.services import OhlcService


class OhlcConnector(FetchConnector):
    def __init__(self, client: KrakenApiClient | None = None):
        self.client = client or KrakenApiClient()
        self.service = OhlcService(self.client)

    def fetch(self, pair: str, interval: int, start: int) -> list[OhlcCandle]:
        '''
        Fetch OHLC (candlestick) data for a trading pair from Kraken.

        :param pair: Trading pair in Kraken format, e.g., 'XXBTZGBP'.
        :param interval: Candle interval in minutes (1, 5, 15, 30, 60, 240, 1440, 10080, 21600).
        :param start: Start timestamp in Unix seconds.
        :return: List of OHLC candle objects.

        Note:
            Kraken always appends the currently-forming (not-yet-committed) candle as the
            last element, regardless of the value of ``start``. The second-to-last element
            ``[-2]`` is the most recent fully committed candle.
        '''
        raw_candles = self.service.fetch_ohlc(pair, interval, start)
        return self._to_domain(raw_candles)

    def _to_domain(self, raw_candles: list[list[int | float]]) -> list[OhlcCandle]:
        '''
        Convert raw Kraken OHLC arrays to OHLC domain objects.

        :param raw_candles: List of raw OHLC arrays from Kraken API.
        :return: List of OhlcCandle domain objects.
        :raises ValueError: If OHLC data is malformed.
        '''
        candles = []
        for candle in raw_candles:
            if len(candle) < 8:
                raise ValueError(f'OHLC data incomplete: expected 8 fields, got {len(candle)}')
            try:
                candles.append(OhlcCandle(
                    timestamp=int(candle[0]),
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    vwap=float(candle[5]),
                    volume=float(candle[6]),
                    count=int(candle[7])
                ))
            except (ValueError, TypeError) as e:
                raise ValueError(f'Failed to parse OHLC data: {candle}. Error: {e}')

        return candles
