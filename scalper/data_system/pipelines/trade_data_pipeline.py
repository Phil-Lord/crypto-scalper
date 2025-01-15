import os
import pandas as pd

from api import KrakenApiClient
from services import TradesService


class TradeDataPipeline:
    def __init__(self, pair: str, since: int, until: int):
        client = KrakenApiClient()
        self.service = TradesService(client)

        self.pair = pair
        self.since = since
        self.until = until

    def update_stored_trades(self):
        trades_raw = self.service.fetch_trades(self.pair, self.since, self.until)
        trades_df = self.__convert_trades_to_df(trades_raw)
        self.__store_trades(trades_df)

    def __convert_trades_to_df(self, trades_raw):
        # Convert raw data into a DataFrame.
        columns = ['price', 'volume', 'time', 'buy/sell',
                   'market/limit', 'miscellaneous', 'trade_id']
        trades_df = pd.DataFrame(trades_raw, columns=columns)

        # Clean data and set the index to trade_id.
        trades_df.dropna(inplace=True)
        trades_df = trades_df.drop_duplicates(subset='trade_id').set_index('trade_id')

        # Drop miscellaneous column and convert timestamps to datetimes.
        trades_df.drop(columns=['miscellaneous'], inplace=True)
        trades_df['time'] = pd.to_datetime(trades_df['time'], unit='s')

        return trades_df

    def __store_trades(self, new_trades_df):
        # Read existing stored trade data.
        if not os.path.exists(f'{self.pair}-trades.csv'):
            columns = ['price', 'volume', 'time', 'buy/sell', 'market/limit', 'trade_id']
            empty_df = pd.DataFrame(columns=columns).set_index('trade_id')
            empty_df.to_csv(f'./{self.pair}-trades.csv')

        stored_trades_df = pd.read_csv(f'./{self.pair}-trades.csv', index_col='trade_id')

        # Filter out any new trades found in the existing stored data, then concatenate and sort.
        new_trades_df = new_trades_df[~new_trades_df.index.isin(stored_trades_df.index)]
        trades_df = pd.concat([stored_trades_df, new_trades_df])
        trades_df.sort_index(inplace=True)

        trades_df.to_csv(f'{self.pair}-trades.csv')
