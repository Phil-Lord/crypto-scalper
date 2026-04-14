import threading
import time

import requests
from typing import Any

from .exceptions import (
    KrakenTooManyRequestsError,
    KrakenApiResponseError,
    KrakenNetworkError,
    KrakenParseError,
)
from exchange_connector.kraken_utils import get_headers


class KrakenApiClient:
    '''
    Low-level HTTP client for the Kraken API.

    Handles request construction, authentication headers, and error parsing.
    '''

    # Shared across all instances — serialises private API calls so nonces are
    # assigned and dispatched in strict order, preventing EAPI:Invalid nonce
    # errors when multiple bots share the same API key.
    _private_lock = threading.Lock()
    _last_nonce: int = 0

    BASE_URL = 'https://api.kraken.com'

    def make_request(self, method: str, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        '''
        Make an HTTP request to the Kraken API.

        :param method: HTTP method ('GET' or 'POST').
        :param endpoint: API endpoint path, e.g., '/0/public/Ticker'.
        :param params: Request parameters.
        :return: Parsed JSON response.
        :raises KrakenNetworkError: If network request fails.
        :raises KrakenParseError: If response cannot be parsed as JSON.
        :raises KrakenTooManyRequestsError: If API rate limit is exceeded.
        :raises KrakenApiResponseError: If API returns an error response.
        '''
        if method.upper() not in ('GET', 'POST'):
            raise ValueError(f'Unsupported HTTP method: {method}')
        try:
            url = self.BASE_URL + endpoint
            if method.upper() == 'GET':
                response = requests.get(url, params=params, timeout=10)
            elif method.upper() == 'POST':
                with KrakenApiClient._private_lock:
                    post_params = {**params, 'nonce': self._next_nonce()}
                    headers = get_headers(post_params, endpoint)
                    response = requests.post(url, data=post_params, headers=headers, timeout=10)
            response.raise_for_status()
            json_response = response.json()
            self._handle_errors(json_response)
            return json_response
        except requests.RequestException as e:
            raise KrakenNetworkError(f'Error making request to {endpoint}: {e}')
        except ValueError as e:
            raise KrakenParseError(f'Failed to parse JSON response: {e}')

    def _next_nonce(self) -> str:
        '''Must be called inside _private_lock.'''
        KrakenApiClient._last_nonce = max(time.time_ns(), KrakenApiClient._last_nonce + 1)
        return str(KrakenApiClient._last_nonce)

    def _handle_errors(self, response: dict[str, Any]) -> None:
        if 'error' in response and response['error']:
            if response['error'] == ['EGeneral:Too many requests']:
                raise KrakenTooManyRequestsError()
            else:
                raise KrakenApiResponseError(f'API Error: {response["error"]}')
