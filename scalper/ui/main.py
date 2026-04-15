from nicegui import app, ui

app.add_static_files('/static', 'ui/static')


@ui.page('/')
def index():
    ui.dark_mode().enable()

    with ui.column().classes('w-full max-w-6xl mx-auto p-8'):
        ui.label('Backtesting Engine').classes('text-3xl font-bold')


def main():
    ui.run(
        title='Scalper',
        favicon='ui/static/dog-park-96x96.png',
        port=8080,
        reload=True,
    )

# Colours:
# #3ecf8e - light green
# #016339 - dark green
