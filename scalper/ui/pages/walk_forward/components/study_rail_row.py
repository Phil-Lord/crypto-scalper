from collections.abc import Callable
from typing import Literal

from nicegui import ui

from ui.theme import StatusPill
from utils import StudySummary


LastRunState = Literal['running', 'idle']


def StudyRailRow(
    study: StudySummary,
    active: bool,
    last_run_state: LastRunState,
    on_click: Callable[[], None],
) -> None:
    '''
    One row in the studies rail on the left of the walk-forward page.

    Consists of two rows:
    1. Study name and, when running, a``LIVE`` pill.
    2. Trial count and best in-sample value.

    Clicking the row selects the study.

    :param study: Summary returned from ``utils.list_studies``.
    :param active: ``True`` if this row is the currently selected study —
        renders with a left accent bar and a slightly brighter background.
    :param last_run_state: ``'running'`` while a phase is mid-flight against
        this study, otherwise ``'idle'``. Cancelled and errored runs both
        collapse to ``'idle'`` (the rail does not surface terminal failure
        states; the relevant section pill does).
    :param on_click: Invoked with no arguments when the row is clicked.
    '''
    if last_run_state not in ('running', 'idle'):
        raise ValueError(
            f'Unknown StudyRailRow last_run_state {last_run_state!r}; '
            f'expected "running" or "idle"'
        )

    bg = 'bg-neutral-800/50' if active else 'hover:bg-neutral-900'
    accent = 'border-emerald-500' if active else 'border-transparent'
    row = ui.element('div').classes(
        'w-full px-4 py-3 cursor-pointer border-b border-neutral-800 '
        f'border-l-2 {accent} {bg}'
    )
    row.on('click', lambda _e: on_click())

    with row:
        with ui.row().classes('w-full items-start justify-between gap-2 no-wrap'):
            ui.label(study.name).classes(
                'text-xs font-mono text-neutral-200 leading-tight break-all'
            )
            if last_run_state == 'running':
                StatusPill('running', 'LIVE')
        with ui.row().classes('w-full items-center gap-3 mt-2'):
            best_is_text = (
                f'{study.best_is:.2f}' if study.best_is is not None else '—'
            )
            ui.label(f'trials {study.trial_count}').classes(
                'text-[11px] font-mono text-neutral-400'
            )
            ui.label(f'IS {best_is_text}').classes(
                'text-[11px] font-mono text-neutral-400'
            )
