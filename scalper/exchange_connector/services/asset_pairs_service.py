import logging

from .kraken_service import KrakenService


class AssetPairsService(KrakenService):
    def fetch_asset_pairs(self, pair: str) -> dict[str, any]:
        self.validate_pair(pair)
        logging.basicConfig(level=logging.INFO)

        return self.make_request('GET', '/0/public/AssetPairs', {'pair': pair})
