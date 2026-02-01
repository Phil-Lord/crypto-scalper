from typing import Any

from .base_connectors import FetchConnector
from exchange_connector.api import KrakenApiClient
from exchange_connector.services import TickerService


class TickerConnector(FetchConnector):
    def __init__(self, client: KrakenApiClient = None):
        self.client = client or KrakenApiClient()
        self.service = TickerService(self.client)

    def fetch(self, pair: str) -> dict[str, Any]:
        '''
        Fetch ticker (current price) data for a trading pair from Kraken.

        :param pair: Trading pair in Kraken format, e.g., 'XXBTZGBP'.
        :return: Ticker data including bid, ask, last trade, volume, etc.
        '''
        return self.service.fetch_ticker(pair)
