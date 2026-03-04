from typing import List

from .base_connectors import FetchConnector
from exchange_connector.api import KrakenApiClient
from exchange_connector.models import QueryOrderResult
from exchange_connector.services import QueryOrdersService


class QueryOrdersConnector(FetchConnector):
    def __init__(self, client: KrakenApiClient | None = None):
        self.client = client or KrakenApiClient()
        self.service = QueryOrdersService(self.client)

    def fetch(self, txids: List[str]) -> List[QueryOrderResult]:
        '''
        Fetch order details.

        :param txids: List of transaction IDs to query.
        :return: List of QueryOrderResult domain objects containing order details.
        '''
        raw_result = self.service.fetch_orders(','.join(txids))
        return self._to_domain(raw_result)

    def _to_domain(self, raw_result: dict) -> List[QueryOrderResult]:
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
                    price=order_data.get('price'),
                    volume=order_data.get('vol_exec'),
                    fee=order_data.get('fee'),
                    status=order_data.get('status'),
                ))
            return results
        except (AttributeError, TypeError) as e:
            raise ValueError(f'Failed to parse order result: {raw_result}. Error: {e}')
