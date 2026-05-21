'''
Studies rail for the walk-forward page.

Owns the rail container, the scrollable list of :class:`StudyRailRow` rows,
the ``+ NEW STUDY`` button, and the load/select/refresh flows that mutate the
page's selection state.
'''
from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from ui.services import list_studies
from ui.theme import BORDER, MONO_CAPTION_CLASSES, muted, primary_button
from utils import StudySummary

from .components import StudyRailRow

if TYPE_CHECKING:
    from . import WalkForwardPage


RAIL_WIDTH_PX = 320


def load_studies() -> list[StudySummary]:
    '''
    Fetch studies for the rail.

    Ordered most-recently-active-first by reversing the service's creation-order output,
    so the default selection sits at the top of the rail.
    '''
    try:
        return list(reversed(list_studies()))
    except Exception as e:
        ui.notify(f'Could not list studies: {e}', type='negative')
        return []


def render_rail(page: WalkForwardPage) -> None:
    with ui.column().classes(
        f'h-full border-r {BORDER} gap-0 shrink-0'
    ).style(f'width: {RAIL_WIDTH_PX}px'):
        with ui.row().classes(
            'w-full items-baseline justify-between px-4 pt-4 pb-3 no-wrap'
        ):
            ui.label('Studies').classes(
                'text-sm uppercase tracking-wider text-neutral-300 font-semibold'
            )
            ui.label(str(len(page._studies))).classes(
                f'{MONO_CAPTION_CLASSES} text-neutral-500'
            )

        page._rail_list = ui.column().classes(
            'flex-1 min-h-0 w-full gap-0 overflow-y-auto'
        )
        render_rail_rows(page)

        with ui.row().classes(
            f'w-full px-4 py-3 border-t {BORDER} no-wrap'
        ):
            page.new_study_button = primary_button(
                '+ NEW STUDY', on_click=page._on_new_study
            )


def render_rail_rows(page: WalkForwardPage) -> None:
    page._rail_list.clear()
    with page._rail_list:
        if not page._studies:
            muted('No studies yet.').classes('px-4 py-3')
            return
        for study in page._studies:
            is_selected = (
                page._selected_study is not None
                and study.name == page._selected_study.name
            )
            is_running = (
                page.phase_mutex.is_busy
                and study.name == page._running_study_name
            )
            StudyRailRow(
                study,
                active=is_selected,
                last_run_state='running' if is_running else 'idle',
                on_click=lambda s=study: _select_study(page, s),
            )


def _select_study(page: WalkForwardPage, study: StudySummary) -> None:
    if page._selected_study is not None and study.name == page._selected_study.name:
        return
    page._selected_study = study
    page._rerender_all()


def refresh_rail(page: WalkForwardPage, select_name: str | None = None) -> None:
    '''
    Reload studies and re-render the rail. When ``select_name`` matches a
    study, that study becomes the selection; otherwise the existing
    selection is preserved if it still exists.
    '''
    page._studies = load_studies()
    target_name = select_name or (
        page._selected_study.name if page._selected_study is not None else None
    )
    if target_name is not None:
        match = next((s for s in page._studies if s.name == target_name), None)
        page._selected_study = match if match is not None else (
            page._studies[0] if page._studies else None
        )
    else:
        page._selected_study = page._studies[0] if page._studies else None

    page._rerender_all()
