import base64
import hashlib
import hmac
import logging
import time
import urllib

from .kraken_service import KrakenService
from utils import get_env_var


class AddOrderService(KrakenService):
    def add_order(self, pair: str, signal: str) -> dict:
        self.validate_pair(pair)
        logging.basicConfig(level=logging.INFO)

        endpoint = '/0/private/AddOrder'
        public_key = get_env_var('KRAKEN_TRADING_API_KEY')
        private_key = get_env_var('KRAKEN_TRADING_API_SECRET')
        nonce = self.get_nonce()

        params = {
            'nonce': nonce,
            'ordertype': 'market',
            'type': signal,
            'pair': pair,
            'oflags': 'viqc',
            'volume': '1'
        }
        headers = {
            'API-Key': public_key,
            'API-Sign': self.get_signature(private_key, params, nonce, endpoint)
        }

        return self.make_request('POST', endpoint, params, headers)

    def get_nonce(self) -> str:
        return str(int(time.time() * 1000))

    def get_signature(self, private_key: str, params: str, nonce: str, endpoint: str) -> str:
        post_params = urllib.parse.urlencode(params)
        message = endpoint.encode() + hashlib.sha256((nonce + post_params).encode()).digest()
        return self.sign(private_key, message)

    def sign(self, private_key: str, message: bytes) -> str:
        return base64.b64encode(
            hmac.new(
                key=base64.b64decode(private_key),
                msg=message,
                digestmod=hashlib.sha512
            ).digest()
        ).decode()
