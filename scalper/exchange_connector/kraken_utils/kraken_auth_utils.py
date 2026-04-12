import base64
import hashlib
import hmac
import os
import time
import urllib


def get_nonce() -> str:
    return str(time.time_ns())


def get_headers(params: dict, endpoint: str) -> dict[str, str]:
    public_key = os.getenv('KRAKEN_TRADING_API_KEY')
    private_key = os.getenv('KRAKEN_TRADING_API_SECRET')

    if not public_key or not private_key:
        raise ValueError('Kraken API keys are not set in environment variables.')

    return {
        'API-Key': public_key,
        'API-Sign': get_signature(private_key, params, params['nonce'], endpoint)
    }


def get_signature(private_key: str, params: dict, nonce: str, endpoint: str) -> str:
    '''
    Generate the API signature for request authentication.

    :param private_key: Kraken API private key (base64 encoded).
    :param params: Request parameters.
    :param nonce: Request nonce.
    :param endpoint: API endpoint path.
    :return: Base64-encoded HMAC-SHA512 signature.
    '''
    post_params = urllib.parse.urlencode(params)
    message = endpoint.encode() + hashlib.sha256((nonce + post_params).encode()).digest()
    return sign(private_key, message)


def sign(private_key: str, message: bytes) -> str:
    '''
    Sign a message with HMAC-SHA512.

    :param private_key: Base64-encoded private key.
    :param message: Message bytes to sign.
    :return: Base64-encoded signature.
    '''
    return base64.b64encode(
        hmac.new(
            key=base64.b64decode(private_key),
            msg=message,
            digestmod=hashlib.sha512
        ).digest()
    ).decode()
