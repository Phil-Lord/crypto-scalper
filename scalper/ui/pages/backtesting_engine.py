from nicegui import ui

from ui.components.chart import build_chart
from ui.components.header import render_header
from ui.components.sidebar import render_sidebar
from ui.services.trades import get_trades
from ui.theme import primary_button, sidebar_input, sidebar_label, sidebar_select


@ui.page('/')
def backtesting_engine():
    ui.dark_mode().enable()
    render_header()

    with render_sidebar():
        sidebar_label('Symbol')
        symbol = sidebar_select(['XXBTZGBP', 'XETHZGBP'], value='XXBTZGBP')

        sidebar_label('Start date')
        start_date = sidebar_input(value='2026-04-01')

        sidebar_label('End date')
        end_date = sidebar_input(value='2026-04-15')

        ui.space()
        primary_button(
            'Load Trades',
            on_click=lambda: chart.update_figure(build_chart(
                get_trades(symbol.value, start_date.value, end_date.value)))
        )

    chart = ui.plotly(build_chart([])).classes('w-full h-full gap-4')
