from nicegui import app, ui

from .pages import backtesting_engine

app.add_static_files('/static', 'ui/static')


def main():
    ui.run(
        title='Scalper',
        favicon='ui/static/dog-park-96x96.png',
        port=8080,
        reload=True
    )

# Colours:
# #3ecf8e - light green (icons)
# #03c574 - bright green (links - white on hover)
# #016339 - dark green (buttons)
