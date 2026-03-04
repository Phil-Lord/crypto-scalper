from typing import Any

from exchange_connector.kraken_utils import get_nonce
from .kraken_service import KrakenService


class QueryOrdersService(KrakenService):
    def fetch_orders(self, txid: str) -> dict[str, Any]:
        endpoint = '/0/private/QueryOrders'
        params = {'nonce': get_nonce(), 'txid': txid}

        return self.make_request('POST', endpoint, params)
