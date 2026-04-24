import pandas as pd
from nicegui import ui


def render_table() -> ui.table:
    data = pd.DataFrame()
    return ui.table.from_pandas(data).classes('max-h-full w-full')


def update_table(table: ui.table, data: pd.DataFrame):
    table.update_from_pandas(data)
