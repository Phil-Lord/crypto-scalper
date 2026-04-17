from nicegui import ui

from ui.components.chart import build_chart
from ui.services.trades import get_trades
from ui.theme import GREEN_DARK


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
