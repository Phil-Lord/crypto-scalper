import logging

from exchange_connector.kraken_utils import get_nonce
from .kraken_service import KrakenService


class AddOrderService(KrakenService):
    def add_order(self, pair: str, signal: str, volume: float) -> dict:
        self.validate_pair(pair)
        logging.basicConfig(level=logging.INFO)

        endpoint = '/0/private/AddOrder'
        params = {
            'nonce': get_nonce(),
            'ordertype': 'market',
            'type': signal,
            'pair': pair,
            'volume': volume
        }
        if signal == 'buy':
            params['oflags'] = 'viqc'

        return self.make_request('POST', endpoint, params)
