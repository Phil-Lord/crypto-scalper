import pandas as pd

from data_system import SQLAlchemyClient, SQLAlchemyTradeRepository
from utils import get_second_timestamp, parse_datetime


def get_trades(pair: str, start_date: str, end_date: str) -> pd.DataFrame:
    client = SQLAlchemyClient()
    repository = SQLAlchemyTradeRepository(client)

    start = get_second_timestamp(*parse_datetime(start_date))
    end = get_second_timestamp(*parse_datetime(end_date))

    trades = repository.get(pair, start, end)
    trades_df = pd.DataFrame([{'timestamp': t.timestamp, 'price': t.price} for t in trades])
    trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'], unit='s')
    return trades_df
