from nicegui import ui
import pandas as pd


def render_table() -> ui.table:
    return ui.table.from_pandas(pd.DataFrame()).classes('w-full h-full')
