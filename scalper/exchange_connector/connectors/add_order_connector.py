from .base_connectors import PlaceConnector
from exchange_connector.api import KrakenApiClient
from exchange_connector.services import AddOrderService


class AddOrderConnector(PlaceConnector):
    def __init__(self, client: KrakenApiClient = None):
        self.client = client or KrakenApiClient()
        self.service = AddOrderService(self.client)

    def place(self, pair: str, signal: str, volume: float) -> dict:
        '''
        Place a market order.

        :param pair: Trading pair in Kraken format, e.g., 'XXBTZGBP'.
        :param signal: Order direction - 'buy' or 'sell'.
        :param volume: Order volume (quote currency for buy, base for sell).
        :return: Order result from Kraken API.
        '''
        return self.service.add_order(pair, signal, volume)
