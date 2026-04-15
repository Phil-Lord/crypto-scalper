from nicegui import ui


@ui.page('/')
def backtesting_engine():
    ui.dark_mode().enable()

    with ui.column().classes('w-full max-w-6xl mx-auto p-8'):
        ui.label('Backtesting Engine').classes('text-3xl font-bold')
