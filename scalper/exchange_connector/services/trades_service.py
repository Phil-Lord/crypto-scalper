from .kraken_service import KrakenService


class TradesService(KrakenService):
    def fetch_trades(self, pair: str, since: int, until: int) -> list[dict]:
        self.validate_pair(pair)
        trades = []
        current_since = since

        while current_since < until:
            params = {'pair': pair, 'since': current_since}
            result = self.fetch_data('Trades', params)
            trades.extend(result[pair][:-1])
            current_since = int(result['last'])

        return trades
