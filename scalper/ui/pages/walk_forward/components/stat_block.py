from nicegui import ui

from ui.theme import caption


def StatBlock(label: str, value: str, highlight: bool = False) -> None:
    '''
    Small label-over-value pair used by the walk-forward context strip.

    :param label: Short label, converted to uppercase (e.g. ``Strategy``, ``Best IS``).
    :param value: Mono-spaced value rendered beneath the label.
    :param highlight: When ``True``, render the value in the accent green —
        used for the ``Best IS`` reading.
    '''
    value_color = 'text-emerald-400' if highlight else 'text-neutral-100'
    with ui.column().classes('gap-0.5 items-start'):
        caption(label)
        ui.label(value).classes(f'text-sm font-mono {value_color}')
