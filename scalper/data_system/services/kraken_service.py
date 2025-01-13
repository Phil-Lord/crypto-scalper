import logging
from typing import Any, Dict

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_log, after_log

from api import KrakenTooManyRequestsError, KrakenApiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KrakenService:
    def __init__(self, client: KrakenApiClient):
        self.client = client

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=30),  # Exponential backoff: 1s, 2s, 4s, ...
        retry=retry_if_exception_type(KrakenTooManyRequestsError),
        before=before_log(logger, logging.INFO),
        after=after_log(logger, logging.INFO)
    )
    def fetch_data(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        response = self.client.make_request(endpoint, params)
        self.client.handle_errors(response)
        return response['result']

    def validate_pair(self, pair: str) -> None:
        if not pair:
            raise ValueError('Trading pair cannot be empty.')
        if not isinstance(pair, str) or len(pair) < 6:
            raise ValueError(f'Invalid trading pair: {pair}.')
