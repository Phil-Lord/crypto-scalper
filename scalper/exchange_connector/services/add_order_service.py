import logging

from exchange_connector.utils import get_nonce
from .kraken_service import KrakenService


class AddOrderService(KrakenService):
    def add_order(self, pair: str, signal: str) -> dict:
        self.validate_pair(pair)
        logging.basicConfig(level=logging.INFO)

        endpoint = '/0/private/AddOrder'
        params = {
            'nonce': get_nonce(),
            'ordertype': 'market',
            'type': signal,
            'pair': pair,
            'oflags': 'viqc',
            'volume': '1'
        }

        return self.make_request('POST', endpoint, params)
