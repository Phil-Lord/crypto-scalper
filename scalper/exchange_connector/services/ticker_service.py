from .kraken_service import KrakenService


class TickerService(KrakenService):
    def fetch_ticker(self, pair: str) -> dict:
        self.validate_pair(pair)
        return self.fetch_data('Ticker', {'pair': pair})[pair]
