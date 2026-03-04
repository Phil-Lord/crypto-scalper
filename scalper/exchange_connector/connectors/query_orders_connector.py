from decimal import Decimal, InvalidOperation

from .base_connectors import FetchConnector
from exchange_connector.api import KrakenApiClient
from exchange_connector.models import QueryOrderResult
from exchange_connector.services import QueryOrdersService


class QueryOrdersConnector(FetchConnector):
    def __init__(self, client: KrakenApiClient | None = None):
        self.client = client or KrakenApiClient()
        self.service = QueryOrdersService(self.client)

    def fetch(self, txids: list[str]) -> list[QueryOrderResult]:
        '''
        Fetch order details.

        :param txids: List of transaction IDs to query.
        :return: List of QueryOrderResult domain objects containing order details.
        '''
        raw_result = self.service.fetch_orders(','.join(txids))
        return self._to_domain(raw_result)

    def _to_domain(self, raw_result: dict) -> list[QueryOrderResult]:
        '''
        Convert raw Kraken QueryOrders response to QueryOrderResult domain objects.

        :param raw_result: Raw API response from Kraken.
        :return: List of QueryOrderResult domain objects.
        :raises ValueError: If response structure is invalid.
        '''
        try:
            results = []
            for order_id, order_data in raw_result.items():
                results.append(QueryOrderResult(
                    txid=order_id,
                    price=Decimal(order_data['price']),
                    volume=Decimal(order_data['vol_exec']),
                    fee=Decimal(order_data['fee']),
                    status=order_data['status'],
                ))
            return results
        except (AttributeError, KeyError, TypeError, InvalidOperation) as e:
            raise ValueError(f'Failed to parse order result: {raw_result}. Error: {e}')
