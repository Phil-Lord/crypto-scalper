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

    def get_trades(self):
        trades_raw = self.service.fetch_trades(self.pair, self.since, self.until)

        stored_trades_df = pd.read_csv('./trades.csv', index_col='trade_id')

        columns = ['price', 'volume', 'time', 'buy/sell',
                   'market/limit', 'miscellaneous', 'trade_id']
        new_trades_df = pd.DataFrame(trades_raw, columns=columns)
        new_trades_df.dropna(inplace=True)
        new_trades_df = new_trades_df.drop_duplicates(subset='trade_id').set_index('trade_id')

        new_trades_df.drop(columns=['miscellaneous'], inplace=True)
        new_trades_df['time'] = pd.to_datetime(new_trades_df['time'], unit='s')

        new_trades_df = new_trades_df[~new_trades_df.index.isin(stored_trades_df.index)]
        trades_df = pd.concat([stored_trades_df, new_trades_df])
        trades_df.sort_index(inplace=True)

        trades_df.to_csv('trades.csv')
