from nicegui import ui


def render_sidebar() -> ui.left_drawer:
    return ui.left_drawer().classes('bg-neutral-900 border-r border-neutral-800 p-4 gap-4')
