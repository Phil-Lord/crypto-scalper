from nicegui import ui

from ui.theme import BORDER, nav_link


def render_header() -> ui.header:
    with ui.header().classes(
        f'bg-neutral-900 border-b {BORDER} px-6 py-3 flex items-center gap-6'
    ):
        ui.label('Scalper').classes('text-white font-bold text-lg')
        nav_link('Backtesting', '/')
        nav_link('Walk-forward', '/walk-forward')
        ui.label('Live Trading').classes('text-neutral-500 text-sm cursor-pointer')
