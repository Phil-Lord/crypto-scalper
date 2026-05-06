from nicegui import app, ui

from .pages import backtesting_engine, walk_forward


def main() -> None:
    app.add_static_files('/static', 'ui/static')
    ui.add_css(open('ui/static/theme.css').read(), shared=True)
    ui.run(
        title='Scalper',
        favicon='ui/static/dog-park-96x96.png',
        port=8080,
        reload=True
    )
