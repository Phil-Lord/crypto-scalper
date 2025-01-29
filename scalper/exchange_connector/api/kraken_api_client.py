import requests

from .exceptions import KrakenTooManyRequestsError


class KrakenApiClient:
    BASE_URL = 'https://api.kraken.com/0/public/'

    def make_request(self, endpoint: str, params: dict[str, any]) -> dict[str, any]:
        try:
            response = requests.get(f'{self.BASE_URL}{endpoint}', params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            raise RuntimeError(f'Error making request to {endpoint}.')
        except ValueError:
            raise RuntimeError('Failed to parse JSON response.')

    def handle_errors(self, response: dict[str, any]) -> None:
        if 'error' in response and response['error']:
            if response['error'] == ['EGeneral:Too many requests']:
                raise KrakenTooManyRequestsError()
            else:
                raise RuntimeError(f'API Error: {response['error']}.')
