from .kraken_service import KrakenService


class OhlcService(KrakenService):
    def fetch_ohlc(self, pair: str, interval: int, since: int) -> list[list[int | float]]:
        self.validate_pair(pair)
        params = {'pair': pair, 'interval': interval, 'since': since}
        return self.make_request('GET', '/0/public/OHLC', params)[pair]
