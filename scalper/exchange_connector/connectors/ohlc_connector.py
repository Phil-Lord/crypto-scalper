from typing import Any

from .base_connectors import FetchConnector
from api import KrakenApiClient
from services import OhlcService


class OhlcConnector(FetchConnector):
    def __init__(self):
        self.client = KrakenApiClient()
        self.service = OhlcService(self.client)

    def fetch(self, pair: str, interval: int, start: int) -> list[list[Any]]:
        return self.service.fetch_ohlc(pair, interval, start)
