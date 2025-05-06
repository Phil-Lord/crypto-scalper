import base64
import hashlib
import hmac
import time
import urllib

from utils import get_env_var


def get_nonce() -> str:
    return str(int(time.time() * 1000))


def get_headers(params: str, endpoint: str) -> dict:
    public_key = get_env_var('KRAKEN_TRADING_API_KEY')
    private_key = get_env_var('KRAKEN_TRADING_API_SECRET')

    return {
        'API-Key': public_key,
        'API-Sign': get_signature(private_key, params, params['nonce'], endpoint)
    }


def get_signature(private_key: str, params: str, nonce: str, endpoint: str) -> str:
    post_params = urllib.parse.urlencode(params)
    message = endpoint.encode() + hashlib.sha256((nonce + post_params).encode()).digest()
    return sign(private_key, message)


def sign(private_key: str, message: bytes) -> str:
    return base64.b64encode(
        hmac.new(
            key=base64.b64decode(private_key),
            msg=message,
            digestmod=hashlib.sha512
        ).digest()
    ).decode()
