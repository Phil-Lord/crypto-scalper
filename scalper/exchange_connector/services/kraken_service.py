import logging

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_log, after_log

from exchange_connector.api import KrakenTooManyRequestsError, KrakenApiClient

logger = logging.getLogger(__name__)


class KrakenService:
    '''
    Base service class for Kraken API operations.

    Provides retry logic with exponential backoff for rate-limited requests
    and common validation methods. All specific services inherit from this.
    '''

    def __init__(self, client: KrakenApiClient):
        self.client = client

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=30),  # Exponential backoff: 1s, 2s, 4s, ...
        retry=retry_if_exception_type(KrakenTooManyRequestsError),
        before=before_log(logger, logging.INFO),
        after=after_log(logger, logging.INFO)
    )
    def make_request(self, method: str, endpoint: str, params: dict) -> dict:
        '''
        Make an API request with automatic retry on rate limiting.

        :param method: HTTP method ('GET' or 'POST').
        :param endpoint: API endpoint path.
        :param params: Request parameters.
        :return: Result data from the API response.
        '''
        response = self.client.make_request(method, endpoint, params)
        return response['result']

    def validate_pair(self, pair: str) -> None:
        if not pair:
            raise ValueError('Trading pair cannot be empty.')
        if not isinstance(pair, str) or len(pair) < 6:
            raise ValueError(f'Invalid trading pair: {pair}.')
