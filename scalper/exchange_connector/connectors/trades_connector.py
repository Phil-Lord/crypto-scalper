from .base_connector import Connector
from exchange_connector.api import KrakenApiClient
from exchange_connector.services import TradesService


class TradesConnector(Connector):
    def __init__(self):
        self.client = KrakenApiClient()
        self.service = TradesService(self.client)

    def fetch(self, pair: str, start: int, end: int) -> list[dict]:
        return self.service.fetch_trades(pair, start, end)
