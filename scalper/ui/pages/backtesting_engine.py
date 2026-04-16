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
            x=[trade.timestamp for trade in trades],
            y=[trade.price for trade in trades],
            mode='lines'
        ))
        fig.update_layout(template='plotly_dark', margin=dict(l=0, r=0, t=0, b=0))

        ui.plotly(fig).classes('w-full h-96')


def get_trades():
    client = SQLAlchemyClient()
    repository = SQLAlchemyTradeRepository(client)

    start = get_second_timestamp(*parse_datetime('2026-4'))
    end = get_second_timestamp(*parse_datetime('2026-4-15'))

    return repository.get('XXBTZGBP', start, end)
