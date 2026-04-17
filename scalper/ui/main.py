from nicegui import app, ui

from .pages import backtesting_engine

app.add_static_files('/static', 'ui/static')


def main() -> None:
    ui.run(
        title='Scalper',
        favicon='ui/static/dog-park-96x96.png',
        port=8080,
        reload=True
    )
