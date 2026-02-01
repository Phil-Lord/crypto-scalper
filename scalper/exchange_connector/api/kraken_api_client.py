import requests
from typing import Any

from .exceptions import KrakenTooManyRequestsError
from exchange_connector.kraken_utils import get_headers


class KrakenApiClient:
    '''
    Low-level HTTP client for the Kraken API.

    Handles request construction, authentication headers, and error parsing.
    '''

    BASE_URL = 'https://api.kraken.com'

    def make_request(self, method: str, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        '''
        Make an HTTP request to the Kraken API.

        :param method: HTTP method ('GET' or 'POST').
        :param endpoint: API endpoint path, e.g., '/0/public/Ticker'.
        :param params: Request parameters.
        :return: Parsed JSON response.
        :raises RuntimeError: If request fails or response cannot be parsed.
        '''
        try:
            url = self.BASE_URL + endpoint
            if method.upper() == 'GET':
                response = requests.get(url, params=params)
            elif method.upper() == 'POST':
                headers = get_headers(params, endpoint)
                response = requests.post(url, data=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            raise RuntimeError(f'Error making request to {endpoint}.')
        except ValueError:
            raise RuntimeError('Failed to parse JSON response.')

    def handle_errors(self, response: dict[str, Any]) -> None:
        if 'error' in response and response['error']:
            if response['error'] == ['EGeneral:Too many requests']:
                raise KrakenTooManyRequestsError()
            else:
                raise RuntimeError(f"API Error: {response['error']}.")
