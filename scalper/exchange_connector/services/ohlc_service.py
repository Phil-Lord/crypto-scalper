from .kraken_service import KrakenService

VALID_OHLC_INTERVALS = {1, 5, 15, 30, 60, 240, 1440, 10080, 21600}


class OhlcService(KrakenService):
    def fetch_ohlc(self, pair: str, interval: int, since: int) -> list[list[int | float | str]]:
        self.validate_pair(pair)
        if interval not in VALID_OHLC_INTERVALS:
            raise ValueError(
                f'Invalid OHLC interval: {interval}. '
                f'Kraken supports: {sorted(VALID_OHLC_INTERVALS)}'
            )
        params = {'pair': pair, 'interval': interval, 'since': since}
        return self.make_request('GET', '/0/public/OHLC', params)[pair]
