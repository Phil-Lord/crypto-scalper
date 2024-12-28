from typing import Any, Dict

from api import KrakenApiClient


class KrakenService:
    def __init__(self, client: KrakenApiClient):
        self.client = client

    def fetch_data(self, endpoint: str, params: Dict[str: Any]) -> Dict[str, Any]:
        response = self.client.make_request(endpoint, params)
        self.client.handle_errors(response)
        return response['result']

    def validate_pair(self, pair: str) -> None:
        if not pair:
            raise ValueError('Trading pair cannot be empty.')
        if not isinstance(pair, str) or len(pair) < 6:
            raise ValueError(f'Invalid trading pair: {pair}.')
