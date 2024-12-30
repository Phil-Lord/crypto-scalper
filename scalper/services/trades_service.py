from typing import Any, Dict

from kraken_service import KrakenService


class TradesService(KrakenService):
    def fetch_trades(self, pair: str) -> Dict[str, Any]:
        pass
