import pandas as pd
from nicegui import ui
import plotly.graph_objects as go

from ui.theme import GREEN_BRIGHT, GREEN_DARK
from ui.services.trades import get_trades


@ui.page('/')
def backtesting_engine():
    ui.dark_mode().enable()

    with ui.header().classes('bg-neutral-900 border-b border-neutral-800 px-6 py-3 flex items-center gap-6'):
        ui.label('Scalper').classes('text-white font-bold text-lg')
        ui.label('Backtesting').classes('text-neutral-300 text-sm cursor-pointer')
        ui.label('Live Trading').classes('text-neutral-500 text-sm cursor-pointer')

    with ui.left_drawer().classes('bg-neutral-900 border-r border-neutral-800 p-4 gap-4'):
        ui.label('Symbol').classes('text-xs text-neutral-400 uppercase tracking-wide')
        symbol = ui.select(['XXBTZGBP', 'XETHZGBP'], value='XXBTZGBP').classes('w-full')

        ui.label('Start date').classes('text-xs text-neutral-400 uppercase tracking-wide')
        start_date = ui.input(value='2026-04-01').classes('w-full')

        ui.label('End date').classes('text-xs text-neutral-400 uppercase tracking-wide')
        end_date = ui.input(value='2026-04-15').classes('w-full')

        ui.space()
        ui.button(
            'Load Trades',
            color=GREEN_DARK,
            on_click=lambda: chart.update_figure(build_chart(
                get_trades(symbol.value, start_date.value, end_date.value)))
        ).classes('w-full text-white')

    chart = ui.plotly(build_chart([])).classes('w-full h-full gap-4')


def build_chart(trades: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if len(trades):
        fig.add_trace(go.Scatter(
            x=trades['timestamp'],
            y=trades['price'],
            mode='lines',
            line=dict(color=GREEN_BRIGHT)
        ))
    fig.update_layout(
        template='plotly_dark',
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )

    return fig
