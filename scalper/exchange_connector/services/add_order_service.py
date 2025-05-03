import base64
import hashlib
import hmac
import json
import logging
import time

from .kraken_service import KrakenService


class AddOrderService(KrakenService):
    def add_order(self, pair: str, signal: str):
        self.validate_pair(pair)
        logging.basicConfig(level=logging.INFO)

        method = 'POST'
        endpoint = '/0/private/AddOrder'
        public_key = ''
        private_key = ''
        nonce = self.get_nonce()

        body = json.dumps({
            'nonce': nonce,
            'ordertype': 'market',
            'type': signal,
            'pair': pair,
            'oflags': 'viqc',
            'volume': '1'
        })
        headers = {
            'Content-Type': 'application/json',
            'API-Key': public_key,
            'API-Sign': self.get_signature(private_key, body, nonce, endpoint)
        }

        return self.make_request(method, endpoint, body, headers)

    def get_nonce(self) -> str:
        return str(int(time.time() * 1000))

    def get_signature(self, private_key: str, data: str, nonce: str, endpoint: str) -> str:
        message = endpoint.encode() + hashlib.sha256((nonce + data).encode()).digest()
        return self.sign(private_key, message)

    def sign(self, private_key: str, message: bytes) -> str:
        return base64.b64encode(
            hmac.new(
                key=base64.b64decode(private_key),
                msg=message,
                digestmod=hashlib.sha512
            ).digest()
        ).decode()
