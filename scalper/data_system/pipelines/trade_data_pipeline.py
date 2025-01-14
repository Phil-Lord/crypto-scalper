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

        columns = ['price', 'volume', 'time', 'buy/sell',
                   'market/limit', 'miscellaneous', 'trade_id']
        trades_df = pd.DataFrame(trades_raw, columns=columns)
        trades_df.dropna(inplace=True)
        trades_df = trades_df.drop_duplicates(subset='trade_id').set_index('trade_id')

        trades_df.drop(columns=['miscellaneous'], inplace=True)
        trades_df['time'] = pd.to_datetime(trades_df['time'], unit='s')

        trades_df.to_csv('trades.csv')
