from typing import Any

from .base_connectors import FetchConnector
from exchange_connector.api import KrakenApiClient
from exchange_connector.services import OhlcService


class OhlcConnector(FetchConnector):
    def __init__(self, client: KrakenApiClient | None = None):
        self.client = client or KrakenApiClient()
        self.service = OhlcService(self.client)

    def fetch(self, pair: str, interval: int, start: int) -> list[list[Any]]:
        '''
        Fetch OHLC (candlestick) data for a trading pair from Kraken.

        :param pair: Trading pair in Kraken format, e.g., 'XXBTZGBP'.
        :param interval: Candle interval in minutes (1, 5, 15, 30, 60, 240, 1440, 10080, 21600).
        :param start: Start timestamp in Unix seconds.
        :return: List of OHLC candles.
        '''
        return self.service.fetch_ohlc(pair, interval, start)
