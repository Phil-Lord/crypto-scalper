'''
Window tabs for the OOS panel.

Each tab is a display selector for one ``(start, end)`` window in the
``out_of_sample_evaluation`` table. Clicking a tab swaps which scores the
trials table shows; the OOS sidebar inputs are NOT populated from the
click — sidebar inputs always represent a *new* window the user wants to
evaluate (per WF7).

:func:`auto_select_window` is the panel's tab-resolution rule: a window
that is currently being evaluated wins over the most-recently-created
one. The panel computes the selection and the tabs render against it.
'''
from collections.abc import Callable
from datetime import datetime, timezone

from nicegui import ui

from data_system import OosWindowAggregate
from ui.theme import StatusPill


WindowKey = tuple[float, float]


def auto_select_window(
    windows: list[OosWindowAggregate],
    running_window: WindowKey | None,
) -> WindowKey | None:
    '''
    Pick which window the trials table should display.

    ``running_window`` wins so the user always sees scores for whatever is
    being evaluated right now, even before its first row has been
    persisted. Otherwise pick the most-recently-created window.

    ``aggregate_windows`` orders rows ascending by ``start_timestamp``, so
    'most recent' is the last row. Returns ``None`` when there are no
    windows and nothing running.
    '''
    if running_window is not None:
        return running_window
    if not windows:
        return None
    last = windows[-1]
    return (last.start, last.end)


def WindowTabs(
    windows: list[OosWindowAggregate],
    selected: WindowKey | None,
    running_window: WindowKey | None,
    on_select: Callable[[WindowKey], None],
) -> None:
    '''
    Horizontal row of tabs, one per OOS window.

    :param windows: Window aggregates from ``list_oos_windows``.
    :param selected: ``(start_ts, end_ts)`` of the currently displayed
        window, or ``None`` when there are no windows yet.
    :param running_window: ``(start_ts, end_ts)`` of the in-flight OOS
        evaluation, or ``None`` when idle. Drives the LIVE pill on the
        matching tab.
    :param on_select: Invoked with the tab's ``(start_ts, end_ts)`` when
        the user clicks it.
    '''
    if not windows:
        ui.label('No OOS windows yet — evaluate a new window to populate.').classes(
            'text-xs text-neutral-500 px-1 py-2'
        )
        return

    with ui.row().classes('w-full gap-2 flex-wrap'):
        for window in windows:
            key: WindowKey = (window.start, window.end)
            _render_tab(
                window=window,
                key=key,
                is_active=selected == key,
                is_running=running_window == key,
                on_select=on_select
            )


def _render_tab(
    window: OosWindowAggregate,
    key: WindowKey,
    is_active: bool,
    is_running: bool,
    on_select: Callable[[WindowKey], None],
) -> None:
    bg = 'bg-neutral-800/60' if is_active else 'hover:bg-neutral-900'
    border = 'border-emerald-500' if is_active else 'border-neutral-800'
    tab = ui.element('div').classes(
        f'min-w-44 px-3 py-2 cursor-pointer border rounded {bg} {border}'
    )
    tab.on('click', lambda _e: on_select(key))

    with tab:
        with ui.row().classes('w-full items-center justify-between gap-2 no-wrap'):
            ui.label(_format_window(window)).classes(
                'text-[12px] font-mono text-neutral-200'
            )
            if is_running:
                StatusPill('running', 'LIVE')
        with ui.row().classes('w-full items-center gap-3 mt-1 no-wrap'):
            ui.label(f'best {window.best_oos:.3f}').classes(
                'text-[10px] font-mono text-neutral-400'
            )
            ui.label(f'gen {window.generalised_count}').classes(
                'text-[10px] font-mono text-emerald-400'
            )
            ui.label(f'over {window.overfit_count}').classes(
                'text-[10px] font-mono text-red-400'
            )


def _format_window(window: OosWindowAggregate) -> str:
    start = datetime.fromtimestamp(window.start, tz=timezone.utc)
    end = datetime.fromtimestamp(window.end, tz=timezone.utc)
    return f'{start:%Y-%m-%d} → {end:%Y-%m-%d}'
