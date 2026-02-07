import logging
from typing import Any

from .kraken_service import KrakenService


class TickerService(KrakenService):
    def fetch_ticker(self, pair: str) -> dict[str, Any]:
        self.validate_pair(pair)
        return self.make_request('GET', '/0/public/Ticker', {'pair': pair})[pair]
