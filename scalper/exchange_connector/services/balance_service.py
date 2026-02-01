import logging
from typing import Any

from exchange_connector.kraken_utils import get_nonce
from .kraken_service import KrakenService


class BalanceService(KrakenService):
    def fetch_balances(self) -> dict[str, Any]:
        logging.basicConfig(level=logging.INFO)

        endpoint = '/0/private/Balance'
        params = {'nonce': get_nonce()}

        return self.make_request('POST', endpoint, params)
