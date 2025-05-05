from .base_connector import Connector
from api import KrakenApiClient
from services import OhlcService


class OhlcConnector(Connector):
    def __init__(self):
        self.client = KrakenApiClient()
        self.service = OhlcService(self.client)

    def fetch(self, pair: str, interval: int, start: int) -> list[list[any]]:
        return self.service.fetch_ohlc(pair, interval, start)
