from nicegui import ui


GREEN_LIGHT = '#3ecf8e'   # icons
GREEN_BRIGHT = '#03c574'  # links
GREEN_DARK = '#016339'    # buttons


def sidebar_label(text: str) -> ui.label:
    return ui.label(text).classes('text-xs text-neutral-400 uppercase tracking-wide')


def sidebar_input(value: str = '') -> ui.input:
    return ui.input(value=value).classes('w-full')


def sidebar_select(options: list, value: str = '') -> ui.select:
    return ui.select(options, value=value).classes('w-full')


def primary_button(text: str, on_click: callable = None) -> ui.button:
    return ui.button(text, color=GREEN_DARK, on_click=on_click).classes('w-full text-white')
