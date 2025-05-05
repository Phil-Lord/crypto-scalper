from .base_connectors import FetchConnector
from exchange_connector.api import KrakenApiClient
from exchange_connector.services import TradesService


class TradesConnector(FetchConnector):
    def __init__(self):
        self.client = KrakenApiClient()
        self.service = TradesService(self.client)

    def fetch(self, pair: str, start: int, end: int) -> list[list[any]]:
        return self.service.fetch_trades(pair, start, end)
