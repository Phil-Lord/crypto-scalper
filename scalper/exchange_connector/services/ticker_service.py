import logging

from .kraken_service import KrakenService


class TickerService(KrakenService):
    def fetch_ticker(self, pair: str) -> dict:
        self.validate_pair(pair)
        logging.basicConfig(level=logging.ERROR)

        return self.make_request('GET', '/0/public/Ticker', {'pair': pair}, {})[pair]
