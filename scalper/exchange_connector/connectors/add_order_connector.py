from decimal import Decimal

from .base_connectors import PlaceConnector
from exchange_connector.api import KrakenApiClient
from exchange_connector.models import AddOrderResult
from exchange_connector.services import AddOrderService


class AddOrderConnector(PlaceConnector):
    def __init__(self, client: KrakenApiClient | None = None):
        self.client = client or KrakenApiClient()
        self.service = AddOrderService(self.client)

    def place(self, pair: str, signal: str, volume: Decimal, validate: bool = False) -> AddOrderResult:
        '''
        Place a market order.

        :param pair: Trading pair in Kraken format, e.g., 'XXBTZGBP'.
        :param signal: Order direction - 'buy' or 'sell'.
        :param volume: Order volume as Decimal (quote currency for buy, base currency for sell).
        :param validate: If True, validate order without executing. Default is False.
        :return: AddOrderResult domain object containing transaction IDs and order description.
        '''
        raw_result = self.service.add_order(pair, signal, volume, validate)
        return self._to_domain(raw_result)

    def _to_domain(self, raw_result: dict) -> AddOrderResult:
        '''
        Convert raw Kraken AddOrder response to AddOrderResult domain object.

        :param raw_result: Raw API response from Kraken.
        :return: AddOrderResult domain object.
        :raises ValueError: If response structure is invalid.
        '''
        try:
            # txid is only present when order is actually placed (validate=False)
            txid = raw_result.get('txid')
            order_description = raw_result.get('descr', {}).get('order', '')

            if not order_description:
                raise ValueError('Missing order description in response')

            return AddOrderResult(txid=txid, order_description=order_description)
        except (AttributeError, TypeError) as e:
            raise ValueError(f'Failed to parse order result: {raw_result}. Error: {e}')
