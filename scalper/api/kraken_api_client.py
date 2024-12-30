import requests
from typing import Any, Dict


class KrakenApiClient:
    BASE_URL = 'https://api.kraken.com/0/public/'

    def make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = requests.get(f'{self.BASE_URL}{endpoint}', params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f'Error making request to {endpoint}')
        except ValueError:
            raise RuntimeError('Failed to parse JSON repsonse.')

    def handle_errors(self, response: Dict[str, Any]) -> None:
        if 'error' in response and response['error']:
            raise RuntimeError(f'API Error: {response['error']}')
