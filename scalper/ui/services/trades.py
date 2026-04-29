import pandas as pd
import plotly.graph_objects as go

from data_system import SQLAlchemyClient, SQLAlchemyTradeRepository, Trade
from exchange_connector import TradesConnector
from utils import get_nano_timestamp, get_second_timestamp, parse_datetime

MAX_POINTS = 2000


def get_trades(pair: str, start_date: str, end_date: str) -> pd.DataFrame:
    client = SQLAlchemyClient()
    repository = SQLAlchemyTradeRepository(client)

    start = get_second_timestamp(*parse_datetime(start_date)) if start_date else None
    end = get_second_timestamp(*parse_datetime(end_date)) if end_date else None

    trades = repository.get(pair, start, end)
    if not trades:
        raise ValueError('No trades found for the given parameters.')

    return _trades_to_df(trades)


def fetch_trades(pair: str, start_date: str, end_date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    '''
    Fetches trades from the exchange for the given window, stores them locally, and
    returns the trades that were already in the local DB plus the ones newly inserted.

    :return: (existing_trades_df, new_trades_df) — both indexed by timestamp.
        The new dataframe is empty if every fetched trade was already in the local DB.
    '''
    connector = TradesConnector()
    repository = SQLAlchemyTradeRepository(SQLAlchemyClient())

    start_seconds = get_second_timestamp(*parse_datetime(start_date))
    end_seconds = get_second_timestamp(*parse_datetime(end_date))
    start_nanos = get_nano_timestamp(*parse_datetime(start_date))
    end_nanos = get_nano_timestamp(*parse_datetime(end_date))

    existing_trades = repository.get(pair, start_seconds, end_seconds)
    existing_trade_ids = {t.trade_id for t in existing_trades}

    fetched = connector.fetch(pair, start_nanos, end_nanos)

    # Kraken returns trades slightly past the requested end timestamp; drop them so
    # the plotted window matches the user's selection.
    fetched = [t for t in fetched if t.timestamp <= end_seconds]
    repository.add(fetched)

    new_trades = [t for t in fetched if t.trade_id not in existing_trade_ids]

    if not existing_trades and not new_trades:
        raise ValueError('No trades found for the given parameters.')

    return _trades_to_df(existing_trades), _trades_to_df(new_trades)


def plot_trades(
    trades: pd.DataFrame,
    figure: go.Figure,
    new_trades: pd.DataFrame | None = None
) -> go.Figure:
    figure.data = []

    if not trades.empty:
        existing_dim = new_trades is not None
        figure.add_trace(_candlestick_trace(
            trades,
            name='Existing' if existing_dim else 'Trades',
            increasing_colour='#9ca3af' if existing_dim else None,
            decreasing_colour='#4b5563' if existing_dim else None
        ))

    if new_trades is not None and not new_trades.empty:
        figure.add_trace(_candlestick_trace(new_trades, name='Newly fetched'))

    return figure


def _candlestick_trace(
    trades: pd.DataFrame,
    name: str,
    increasing_colour: str | None = None,
    decreasing_colour: str | None = None
) -> go.Candlestick:
    ohlc = convert_prices_to_ohlc(trades)
    kwargs: dict = {
        'x': ohlc['timestamp'],
        'open': ohlc['open'],
        'high': ohlc['high'],
        'low': ohlc['low'],
        'close': ohlc['close'],
        'name': name
    }
    if increasing_colour is not None:
        kwargs['increasing'] = {'line': {'color': increasing_colour},
                                'fillcolor': increasing_colour}
    if decreasing_colour is not None:
        kwargs['decreasing'] = {'line': {'color': decreasing_colour},
                                'fillcolor': decreasing_colour}
    return go.Candlestick(**kwargs)


def convert_prices_to_ohlc(prices: pd.DataFrame) -> pd.DataFrame:
    ''' Converts prices to OHLC, downsampling to a maximum number of points for plotting. '''
    if len(prices) == 0:
        return prices
    interval = max(1, len(prices) // MAX_POINTS)
    ohlc = prices['price'].resample(f'{interval}min').ohlc().dropna()
    return ohlc.reset_index()


def _trades_to_df(trades: list[Trade]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame({'price': []}, index=pd.DatetimeIndex([], name='timestamp'))
    df = pd.DataFrame([{'timestamp': t.timestamp, 'price': t.price} for t in trades])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    df.set_index('timestamp', inplace=True)
    return df
