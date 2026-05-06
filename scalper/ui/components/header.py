from nicegui import ui


def render_header() -> ui.header:
    with ui.header().classes(
        'bg-neutral-900 border-b border-neutral-800 px-6 py-3 flex items-center gap-6'
    ):
        ui.label('Scalper').classes('text-white font-bold text-lg')
        ui.link('Backtesting', '/').classes('text-neutral-300 text-sm cursor-pointer no-underline')
        ui.link('Walk-forward', '/walk-forward').classes(
            'text-neutral-300 text-sm cursor-pointer no-underline'
        )
        ui.label('Live Trading').classes('text-neutral-500 text-sm cursor-pointer')
