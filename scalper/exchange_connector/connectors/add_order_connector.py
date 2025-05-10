from .base_connectors import PlaceConnector
from exchange_connector.api import KrakenApiClient
from exchange_connector.services import AddOrderService


class AddOrderConnector(PlaceConnector):
    def __init__(self):
        self.client = KrakenApiClient()
        self.service = AddOrderService(self.client)

    def place(self, pair: str, signal: str, volume: float) -> dict:
        ''' Place a market order. Buy volume in quote, sell volume in base. '''
        return self.service.add_order(pair, signal, volume)
