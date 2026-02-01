from typing import Any

from tqdm import tqdm

from .kraken_service import KrakenService


class TradesService(KrakenService):
    def fetch_trades(self, pair: str, since: int, until: int) -> list[list[Any]]:
        '''
        Fetch historical trades for a trading pair with automatic pagination.

        :param pair: Trading pair in Kraken format, e.g., 'XXBTZGBP'.
        :param since: Start timestamp in nanoseconds.
        :param until: End timestamp in nanoseconds.
        :return: List of raw trade arrays. Each trade: [price, volume, time, side, type, misc, id].
        '''
        self.validate_pair(pair)
        trades = []
        current_since = since

        with tqdm(total=until - since, desc=f'Fetching', dynamic_ncols=True, bar_format='{l_bar}{bar}') as pbar:
            while current_since < until:
                params = {'pair': pair, 'since': current_since}
                result = self.make_request('GET', '/0/public/Trades', params)
                trades.extend(result[pair][:-1])
                new_since = int(result['last'])

                pbar.update(new_since - current_since)
                current_since = new_since

        return trades
