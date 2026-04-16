import pandas as pd
from nicegui import ui
import plotly.graph_objects as go

from data_system import SQLAlchemyClient, SQLAlchemyTradeRepository
from utils import get_second_timestamp, parse_datetime


@ui.page('/')
def backtesting_engine():
    ui.dark_mode().enable()

    trades = get_trades()

    with ui.column().classes('w-full max-w-6xl mx-auto p-8'):
        ui.label('Backtesting Engine').classes('text-3xl font-bold')

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trades['timestamp'],
            y=trades['price'],
            mode='lines',
            line=dict(color='#3ecf8e')
        ))
        fig.update_layout(template='plotly_dark', margin=dict(l=0, r=0, t=0, b=0))

        ui.plotly(fig).classes('w-full h-96')


def get_trades() -> pd.DataFrame:
    client = SQLAlchemyClient()
    repository = SQLAlchemyTradeRepository(client)

    start = get_second_timestamp(*parse_datetime('2026-4'))
    end = get_second_timestamp(*parse_datetime('2026-4-15'))

    trades = repository.get('XXBTZGBP', start, end)
    trades_df = pd.DataFrame([{'timestamp': t.timestamp, 'price': t.price} for t in trades])
    trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'], unit='s')

    return trades_df
