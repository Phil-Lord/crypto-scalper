'''
Window tabs for the OOS panel.

Each tab is a display selector for one ``(start, end)`` window in the
``out_of_sample_evaluation`` table. Clicking the tab body swaps which
scores the trials table shows; the OOS sidebar inputs are NOT populated
from a body click — sidebar inputs always represent a *new* window the
user wants to evaluate (per WF7).

A small ``↑`` button on each tab copies the window's dates into the
sidebar form. It is the explicit affordance for re-evaluating an
existing window after extending IS, when the top-N trials may have
shifted. The data layer (``get_top_param_sets``) skips trials already
evaluated for the window, so re-running is naturally additive.

:func:`auto_select_window` is the panel's tab-resolution rule: a window
that is currently being evaluated wins over the most-recently-created
one. The panel computes the selection and the tabs render against it.
'''
from collections.abc import Callable
from datetime import datetime, timezone

from nicegui import ui

from data_system import OosWindowAggregate
from ui.theme import BORDER, MONO_CAPTION_CLASSES, StatusPill, muted


WindowKey = tuple[float, float]


def format_window_dates(key: WindowKey) -> tuple[str, str]:
    '''
    Inverse of ``derive_window_key``: ``(start_ts, end_ts)`` floats in UTC
    seconds → ``'YYYY-M-D-h-m-s'`` text pair the sidebar inputs accept.

    Used by the "use as template" tab button to populate the OOS form
    from an existing window.
    '''
    return _format_dt(key[0]), _format_dt(key[1])


def _format_dt(ts: float) -> str:
    # Must stay in UTC to round-trip with utils.get_second_timestamp,
    # which builds the inverse timestamp without applying a TZ offset.
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return f'{dt.year}-{dt.month}-{dt.day}-{dt.hour}-{dt.minute}-{dt.second}'


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
    on_use_as_template: Callable[[WindowKey], None] | None = None,
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
        the tab body is clicked.
    :param on_use_as_template: Invoked with the tab's ``(start_ts, end_ts)``
        when the template button is clicked. Pass ``None`` to hide the
        button — used while OOS is running, when the sidebar inputs are
        not mounted.
    '''
    if not windows:
        muted(
            'No OOS windows yet — evaluate a new window to populate.'
        ).classes('px-1 py-2')
        return

    with ui.row().classes('w-full gap-2 flex-wrap'):
        for window in windows:
            key: WindowKey = (window.start, window.end)
            _render_tab(
                window=window,
                key=key,
                is_active=selected == key,
                is_running=running_window == key,
                on_select=on_select,
                on_use_as_template=on_use_as_template,
            )


def _render_tab(
    window: OosWindowAggregate,
    key: WindowKey,
    is_active: bool,
    is_running: bool,
    on_select: Callable[[WindowKey], None],
    on_use_as_template: Callable[[WindowKey], None] | None,
) -> None:
    bg = 'bg-neutral-800/60' if is_active else 'hover:bg-neutral-900'
    border = 'border-emerald-500' if is_active else BORDER
    tab = ui.element('div').classes(
        f'min-w-44 px-3 py-2 cursor-pointer border rounded {bg} {border}'
    )
    tab.on('click', lambda _e: on_select(key))

    with tab:
        with ui.row().classes('w-full items-center justify-between gap-2 no-wrap'):
            ui.label(_format_window(window)).classes(
                f'{MONO_CAPTION_CLASSES} text-neutral-200'
            )
            with ui.row().classes('items-center gap-1 no-wrap'):
                if is_running:
                    StatusPill('running', 'LIVE')
                if on_use_as_template is not None:
                    button = ui.button(
                        icon='arrow_upward',
                        on_click=lambda _e, k=key: on_use_as_template(k),
                    ).props('flat dense round size=xs').classes(
                        'text-neutral-400'
                    )
                    button.tooltip('Use these dates in the sidebar form.')
                    # Stop the bubble: clicking the icon shouldn't also
                    # fire the tab's body click handler.
                    button.on('click.stop')
        with ui.row().classes('w-full items-center gap-3 mt-1 no-wrap'):
            ui.label(f'best {window.best_oos:.3f}').classes(
                f'{MONO_CAPTION_CLASSES} text-neutral-400'
            )
            ui.label(f'gen {window.generalised_count}').classes(
                f'{MONO_CAPTION_CLASSES} text-emerald-400'
            )
            ui.label(f'over {window.overfit_count}').classes(
                f'{MONO_CAPTION_CLASSES} text-red-400'
            )


def _format_window(window: OosWindowAggregate) -> str:
    start = datetime.fromtimestamp(window.start, tz=timezone.utc)
    end = datetime.fromtimestamp(window.end, tz=timezone.utc)
    return f'{start:%Y-%m-%d} → {end:%Y-%m-%d}'
