import datetime
import time
from typing import Any

import pandas as pd


def get_timestamp(year, month, day, hour, minute, second):
    date = datetime.datetime(year, month, day, hour, minute, second)
    return int(time.mktime(date.timetuple()) * 1000000000)


def format_trades(trades_raw: list[list[Any]]) -> pd.DataFrame:
    '''
    Convert a raw list of trades to a pandas DataFrame, then clean and format the data.
    '''
    # Convert raw data into a DataFrame.
    columns = ['price', 'volume', 'timestamp', 'side', 'order_type', 'miscellaneous', 'trade_id']
    trades_df = pd.DataFrame(trades_raw, columns=columns)

    # Clean data and set the index to trade_id.
    trades_df.dropna(inplace=True)
    trades_df = trades_df.drop_duplicates(subset='trade_id').set_index('trade_id')

    # Drop miscellaneous column.
    trades_df.drop(columns=['miscellaneous'], inplace=True)

    return trades_df
