from .base_connectors import FetchConnector
from exchange_connector.api import KrakenApiClient
from exchange_connector.services import BalanceService


class BalanceConnector(FetchConnector):
    def __init__(self):
        self.client = KrakenApiClient()
        self.service = BalanceService(self.client)

    def fetch(self) -> dict:
        return self.service.fetch_balances()
