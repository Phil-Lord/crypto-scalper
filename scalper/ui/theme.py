from nicegui import ui


GREEN_LIGHT = '#3ecf8e'   # icons
GREEN_BRIGHT = '#03c574'  # links
GREEN_DARK = '#016339'    # buttons


def sidebar_label(text: str) -> ui.label:
    return ui.label(text).classes('text-xs text-neutral-400 uppercase tracking-wide')


def sidebar_input(label: str, value: str = '') -> ui.input:
    return ui.input(label=label, value=value).classes('w-full')


def sidebar_select(label: str, options: list, value: str = '') -> ui.select:
    return ui.select(label=label, options=options, value=value).classes('w-full')


def primary_button(text: str, on_click: callable = None) -> ui.button:
    return ui.button(text, color=GREEN_DARK, on_click=on_click).classes('w-full text-white')
