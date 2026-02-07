import logging
from typing import Any

from .kraken_service import KrakenService


class AssetPairsService(KrakenService):
    def fetch_asset_pairs(self, pair: str) -> dict[str, Any]:
        self.validate_pair(pair)
        return self.make_request('GET', '/0/public/AssetPairs', {'pair': pair})
