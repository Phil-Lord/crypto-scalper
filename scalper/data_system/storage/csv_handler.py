import os

import pandas as pd

from .exceptions import MissingTradesFileException


class CsvHandler:
    def __init__(self, pair: str):
        self.pair = pair
        storage_folder = os.path.join(os.path.dirname(__file__), 'storage')
        os.makedirs(storage_folder, exist_ok=True)
        self.storage_path = f'{storage_folder}/{pair}-trades.csv'

    def save_trades(self, trades: pd.DataFrame):
        # Filter out any new trades found in the existing stored data, then concatenate.
        existing_trades = self.load_trades(True)
        trades = trades[~trades.index.isin(existing_trades.index)]
        trades_df = pd.concat([existing_trades, trades])

        # Sort by trade id and save.
        trades_df.sort_index(inplace=True)
        trades_df.to_csv(self.storage_path)

    def load_trades(self, create_if_missing: bool = False):
        # Check for existing data for the passed pair.
        # If none exists and create_if_missing is True, create and return an empty file.
        if not os.path.exists(self.storage_path):
            if create_if_missing:
                trades = self.__save_empty_file()
                return trades
            else:
                raise MissingTradesFileException(self.pair)

        # Load trades from previously populated csv file.
        return pd.read_csv(self.storage_path, index_col='trade_id')

    def __save_empty_file(self) -> pd.DataFrame:
        '''
        Create, save, and return an empty dataframe matching the trade schema.
        '''
        columns = ['price', 'volume', 'time', 'buy/sell', 'market/limit', 'trade_id']
        empty_df = pd.DataFrame(columns=columns).set_index('trade_id')
        empty_df.to_csv(self.storage_path)
        return empty_df
