import pandas as pd
import plotly.graph_objects as go

from data_system import SQLAlchemyClient, SQLAlchemyTradeRepository
from utils import get_second_timestamp, parse_datetime

MAX_POINTS = 2000


def get_trades(pair: str, start_date: str, end_date: str) -> pd.DataFrame:
    client = SQLAlchemyClient()
    repository = SQLAlchemyTradeRepository(client)

    start = get_second_timestamp(*parse_datetime(start_date)) if start_date else None
    end = get_second_timestamp(*parse_datetime(end_date)) if end_date else None

    trades = repository.get(pair, start, end)
    if not trades:
        raise ValueError('No trades found for the given parameters.')

    trades_df = pd.DataFrame([{'timestamp': t.timestamp, 'price': t.price} for t in trades])
    trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'], unit='s')
    trades_df.set_index('timestamp', inplace=True)
    return trades_df


def plot_trades(trades: pd.DataFrame, figure: go.Figure) -> go.Figure:
    if trades.empty:
        return figure

    ohlc = convert_prices_to_ohlc(trades)
    figure.data = []
    figure.add_trace(go.Candlestick(
        x=ohlc['timestamp'],
        open=ohlc['open'],
        high=ohlc['high'],
        low=ohlc['low'],
        close=ohlc['close']
    ))
    return figure


def convert_prices_to_ohlc(prices: pd.DataFrame) -> pd.DataFrame:
    ''' Converts prices to OHLC, downsampling to a maximum number of points for plotting. '''
    if len(prices) == 0:
        return prices
    interval = max(1, len(prices) // MAX_POINTS)
    ohlc = prices['price'].resample(f'{interval}min').ohlc().dropna()
    return ohlc.reset_index()
