from nicegui import ui

from ui.theme import BORDER


def render_sidebar() -> ui.left_drawer:
    return ui.left_drawer().classes(f'bg-neutral-900 border-r {BORDER} p-4 gap-4')
