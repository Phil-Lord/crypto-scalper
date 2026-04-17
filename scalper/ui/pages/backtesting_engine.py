from nicegui import ui

from ui.components import build_chart, render_header, render_sidebar
from ui.services import get_trades
from ui.theme import primary_button, sidebar_input, sidebar_select


@ui.page('/')
def backtesting_engine():
    ui.dark_mode().enable()
    render_header()

    with render_sidebar():
        symbol = sidebar_select('Symbol', ['XXBTZGBP', 'XETHZGBP'], 'XXBTZGBP')
        start_date = sidebar_input('Start date', '2026-04-01')
        end_date = sidebar_input('End date', '2026-04-15')

        ui.space()
        primary_button(
            'Load Trades',
            on_click=lambda: chart.update_figure(build_chart(
                get_trades(symbol.value, start_date.value, end_date.value)))
        )

    chart = ui.plotly(build_chart([])).classes('w-full h-full gap-4')
