from nicegui import ui
import pandas as pd
import plotly.graph_objects as go

from backtesting_engine import BacktestingEngine
from data_system import SQLAlchemyClient, SQLAlchemyTradeRepository
from strategy_manager import create_strategy
from utils import get_second_timestamp, parse_datetime, PRECISION_TREND_CONFIG

from .trades import convert_prices_to_ohlc


def run_backtest(symbol, start_date, end_date) -> pd.DataFrame:
    strategy = create_strategy('PrecisionTrendStrategy', PRECISION_TREND_CONFIG)
    repo = SQLAlchemyTradeRepository(SQLAlchemyClient())
    start = get_second_timestamp(*parse_datetime(start_date)) if start_date else None
    end = get_second_timestamp(*parse_datetime(end_date)) if end_date else None
    engine = BacktestingEngine(symbol, strategy, repo, start, end, interval=1, vectorised=True)
    return engine.run()


def plot_backtest_results(results: pd.DataFrame, figure: go.Figure) -> go.Figure:
    ohlc = convert_prices_to_ohlc(results)
    figure.data = []

    figure.add_trace(go.Candlestick(
        name='Price',
        x=ohlc['timestamp'],
        open=ohlc['open'],
        high=ohlc['high'],
        low=ohlc['low'],
        close=ohlc['close']
    ))

    buys = results[results['signal'] == 'buy']
    figure.add_trace(create_scatter(buys, 'green'))

    sells = results[results['signal'] == 'sell']
    figure.add_trace(create_scatter(sells, 'red'))

    return figure


def create_scatter(results: pd.DataFrame, colour: str) -> go.Scatter:
    return go.Scatter(
        x=results.index,
        y=results['price'],
        mode='markers',
        marker=go.scatter.Marker(color=colour, symbol='circle', size=12)
    )


def update_table(table: ui.table, results: pd.DataFrame) -> None:
    if results is None or results.empty:
        table.update_from_pandas(pd.DataFrame())
        return

    trades = results[(results['signal'] == 'buy') | (results['signal'] == 'sell')]

    # Format timestamp and price
    trades.reset_index(inplace=True)
    trades['timestamp'] = trades['timestamp'].dt.strftime('%d %b %Y %H:%M')
    trades['price'] = trades['price'].apply(lambda p: f'£{p:,.2f}')

    # Reorder columns to show timestamp, signal, price first
    key_columns = ['timestamp', 'signal', 'price']
    remaining_columns = [c for c in trades.columns if c not in key_columns]
    trades = trades[key_columns + remaining_columns]

    table.update_from_pandas(trades)

    for i in range(len(table.columns)):
        table.columns[i]['sortable'] = True

    # Add conditional colour formatting for signal column
    with table.add_slot('body-cell-signal'):
        with table.cell('signal'):
            ui.badge().props('''
                :color="props.value == 'buy' ? 'green' : 'red'"
                :label="props.value"
            ''')
