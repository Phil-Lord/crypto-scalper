from .base_connectors import FetchConnector
from exchange_connector.api import KrakenApiClient
from exchange_connector.services import AssetPairsService


class AssetPairsConnector(FetchConnector):
    def __init__(self):
        self.client = KrakenApiClient()
        self.service = AssetPairsService(self.client)

    def fetch(self, pair: str) -> dict[str, any]:
        return self.service.fetch_asset_pairs(pair)
