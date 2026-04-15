from decimal import Decimal
from typing import Any

from .kraken_service import KrakenService


class AddOrderService(KrakenService):
    def add_order(self, pair: str, signal: str, volume: Decimal, validate: bool = False) -> dict[str, Any]:
        self.validate_pair(pair)
        endpoint = '/0/private/AddOrder'
        params = {
            'ordertype': 'market',
            'type': signal,
            'pair': pair,
            'volume': volume,
            'validate': validate
        }
        if signal == 'buy':
            params['oflags'] = 'viqc'

        return self.make_request('POST', endpoint, params)
