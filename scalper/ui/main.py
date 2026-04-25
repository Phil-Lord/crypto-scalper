from nicegui import app, ui

from .pages import backtesting_engine

app.add_static_files('/static', 'ui/static')
ui.add_css(open('ui/static/theme.css').read(), shared=True)


def main() -> None:
    ui.run(
        title='Scalper',
        favicon='ui/static/dog-park-96x96.png',
        port=8080,
        reload=True
    )
