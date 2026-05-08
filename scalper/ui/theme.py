from typing import Literal

from nicegui import ui


GREEN_LIGHT = '#3ecf8e'   # icons
GREEN_BRIGHT = '#03c574'  # links
GREEN_DARK = '#016339'    # buttons


PillStatus = Literal['running', 'pending', 'done', 'error', 'cancelled']

_PILL_CLASSES: dict[str, str] = {
    'running': 'bg-amber-900/40 text-amber-300 border-amber-700/60',
    'pending': 'bg-neutral-800 text-neutral-400 border-neutral-700',
    'done': 'bg-emerald-900/40 text-emerald-300 border-emerald-700/60',
    'error': 'bg-red-900/40 text-red-300 border-red-700/60',
    'cancelled': 'bg-neutral-800 text-neutral-500 border-neutral-700',
}


def sidebar_label(text: str) -> ui.label:
    return ui.label(text).classes('text-xs text-neutral-400 uppercase tracking-wide')


def sidebar_input(label: str, value: str = '') -> ui.input:
    return ui.input(label=label, value=value).classes('w-full')


def sidebar_select(label: str, options: list, value: str = '') -> ui.select:
    return ui.select(label=label, options=options, value=value).classes('w-full')


def primary_button(text: str, on_click: callable = None) -> ui.button:
    return ui.button(text, color=GREEN_DARK, on_click=on_click).classes('w-full text-white')


def StatusPill(status: PillStatus, label: str | None = None) -> ui.label:
    '''
    Small status chip used across the walk-forward page
    (rail rows, section headers, worker tiles).

    :param status: One of ``running`` / ``pending`` / ``done`` / ``error`` / ``cancelled``.
        Drives the colour scheme.
    :param label: Optional override for the displayed text.
        Defaults to the upper-cased status name.
    '''
    if status not in _PILL_CLASSES:
        raise ValueError(
            f'Unknown StatusPill status {status!r}; '
            f'expected one of {sorted(_PILL_CLASSES)}'
        )
    text = (label if label is not None else status).upper()
    return ui.label(text).classes(
        'inline-block px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider '
        f'rounded border {_PILL_CLASSES[status]}'
    )
