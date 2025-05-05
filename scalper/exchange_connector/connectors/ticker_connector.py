from .base_connectors import FetchConnector
from exchange_connector.api import KrakenApiClient
from exchange_connector.services import TickerService


class TickerConnector(FetchConnector):
    def __init__(self):
        self.client = KrakenApiClient()
        self.service = TickerService(self.client)

    def fetch(self, pair: str) -> dict:
        return self.service.fetch_ticker(pair)
