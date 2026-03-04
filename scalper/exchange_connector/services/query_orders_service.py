from typing import Any

from .kraken_service import KrakenService


class QueryOrdersService(KrakenService):
    def fetch_orders(self, txid: str) -> dict[str, Any]:
        return self.make_request('POST', '/0/private/QueryOrders', {'txid': txid})
