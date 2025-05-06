import logging

from .kraken_service import KrakenService


class TradesService(KrakenService):
    def fetch_trades(self, pair: str, since: int, until: int) -> list[list[any]]:
        self.validate_pair(pair)
        logging.basicConfig(level=logging.INFO)

        trades = []
        current_since = since

        while current_since < until:
            params = {'pair': pair, 'since': current_since}
            result = self.make_request('GET', '/0/public/Trades', params)
            trades.extend(result[pair][:-1])
            current_since = int(result['last'])

        return trades
