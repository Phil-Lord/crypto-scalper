from typing import Any

from .base_connectors import FetchConnector
from exchange_connector.api import KrakenApiClient
from exchange_connector.services import AssetPairsService


class AssetPairsConnector(FetchConnector):
    def __init__(self, client: KrakenApiClient = None):
        self.client = client or KrakenApiClient()
        self.service = AssetPairsService(self.client)

    def fetch(self, pair: str) -> dict[str, Any]:
        '''
        Fetch asset pair information.

        :param pair: Trading pair in Kraken format, e.g., 'XXBTZGBP'.
        :return: Asset pair details from Kraken API.
        '''
        return self.service.fetch_asset_pairs(pair)
