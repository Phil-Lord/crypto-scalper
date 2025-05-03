from exchange_connector.api import KrakenApiClient
from exchange_connector.services import AddOrderService


class AddOrderConnector():
    def __init__(self):
        self.client = KrakenApiClient()
        self.service = AddOrderService(self.client)

    def add_order(self, pair: str, signal: str) -> dict:
        return self.service.add_order(pair, signal)
