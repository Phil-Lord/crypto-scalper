from .kraken_service import KrakenService


class OhlcService(KrakenService):
    def fetch_ohlc(self, pair: str, interval: int, since: int) -> list[dict[str, any]]:
        self.validate_pair(pair)
        params = {
            'pair': pair,
            'interval': interval,
            'since': since
        }
        return self.fetch_data('OHLC', params)[pair]
