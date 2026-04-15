from typing import Any

from .kraken_service import KrakenService


class BalanceService(KrakenService):
    def fetch_balances(self) -> dict[str, Any]:
        endpoint = '/0/private/Balance'
        params = {}

        return self.make_request('POST', endpoint, params)
