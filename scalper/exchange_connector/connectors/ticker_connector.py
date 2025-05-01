from .base_connector import Connector
from exchange_connector.api import KrakenApiClient
from exchange_connector.services import TickerService


class TickerConnector(Connector):
    def __init__(self):
        self.client = KrakenApiClient()
        self.service = TickerService(self.client)

    def fetch(self, pair: str) -> dict:
        return self.service.fetch_ticker(pair)
