import os
from typing import Any

import pandas as pd

from .exceptions import MissingTradesFileException


class CsvHandler:
    def __init__(self, pair: str):
        self.pair = pair

        # Get the store directory and a create path to the trading-pair-specific csv file.
        storage_folder = os.path.join(os.path.dirname(__file__), 'store')
        os.makedirs(storage_folder, exist_ok=True)
        self.storage_path = f'{storage_folder}/{pair}-trades.csv'

    def save_trades(self, raw_trades: list[list[Any]]) -> None:
        trades = self.__process_raw_trades(raw_trades)

        # Filter out any new trades found in the existing stored data, then concatenate.
        existing_trades = self.load_trades(True)
        trades = trades[~trades.index.isin(existing_trades.index)]
        trades_df = pd.concat([existing_trades, trades])

        # Sort by trade id and save.
        trades_df.sort_index(inplace=True)
        trades_df.to_csv(self.storage_path)

    def load_trades(self, create_if_missing: bool = False) -> pd.DataFrame:
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
        columns = ['price', 'volume', 'timestamp', 'side', 'order_type', 'trade_id']
        empty_df = pd.DataFrame(columns=columns).set_index('trade_id')
        empty_df.to_csv(self.storage_path)
        return empty_df

    def __process_raw_trades(self, raw_trades: list[list[Any]]) -> pd.DataFrame:
        '''
        Convert a raw list of trades to a pandas DataFrame, then clean and format the data.
        '''
        # Convert raw data into a DataFrame.
        columns = ['price', 'volume', 'timestamp', 'side',
                   'order_type', 'miscellaneous', 'trade_id']
        trades_df = pd.DataFrame(raw_trades, columns=columns)

        # Clean data and set the index to trade_id.
        trades_df.dropna(inplace=True)
        trades_df = trades_df.drop_duplicates(subset='trade_id').set_index('trade_id')

        # Drop miscellaneous column.
        trades_df.drop(columns=['miscellaneous'], inplace=True)

        return trades_df
