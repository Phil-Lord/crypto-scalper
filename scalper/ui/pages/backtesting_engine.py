from nicegui import ui

from ui.components.chart import build_chart
from ui.components.header import render_header
from ui.components.sidebar import render_sidebar
from ui.services.trades import get_trades
from ui.theme import GREEN_DARK


@ui.page('/')
def backtesting_engine():
    ui.dark_mode().enable()
    render_header()

    with render_sidebar():
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
