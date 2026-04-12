from typing import Any

from .kraken_service import KrakenService


class QueryOrdersService(KrakenService):
    def fetch_orders(self, txid: str) -> dict[str, Any]:
        endpoint = '/0/private/QueryOrders'
        params = {'txid': txid}

        return self.make_request('POST', endpoint, params)
