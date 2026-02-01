from typing import Any

from .base_connectors import FetchConnector
from exchange_connector.api import KrakenApiClient
from exchange_connector.services import BalanceService


class BalanceConnector(FetchConnector):
    def __init__(self, client: KrakenApiClient = None):
        self.client = client or KrakenApiClient()
        self.service = BalanceService(self.client)

    def fetch(self) -> dict[str, Any]:
        '''
        Fetch account balances.

        :return: Dictionary of asset balances keyed by asset name.
        '''
        return self.service.fetch_balances()
