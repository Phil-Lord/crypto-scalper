'''
``+ NEW STUDY`` flow for the walk-forward page.

Drives the new-study dialog, the optimistic placeholder rail row, and the
launch of the in-sample run under :class:`PhaseMutex`.
'''
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from nicegui import ui

from ui.services import start_in_sample
from ui.services.walk_forward import split_trials
from utils import StudyDirection, StudySummary

from .components import NewStudyForm, derive_study_name, show_new_study_dialog

if TYPE_CHECKING:
    from . import WalkForwardPage


async def on_new_study(page: WalkForwardPage) -> None:
    if page.phase_mutex.is_busy:
        return
    form = await show_new_study_dialog()
    if form is None:
        return
    await start_in_sample_from_form(page, form)


async def start_in_sample_from_form(page: WalkForwardPage, form: NewStudyForm) -> None:
    '''
    Kick off an in-sample run under the page-level mutex.

    Inserts an optimistic placeholder row for the new study and selects it
    immediately, *before* arming the mutex, so that the synchronous
    listener fired by ``PhaseMutex.start`` sees the running name and
    placeholder already in place and produces a single coherent re-render.
    State is rolled back if ``start`` raises.

    The Optuna study only materialises once the subprocess reaches
    ``create_study``, which races with any rail reload here — the
    placeholder ensures the row is visible and selected (and so wears the
    running pill) from the moment the user confirms. Phase-done refresh
    replaces the placeholder with the real summary.

    ``derive_study_name`` returns an empty string when its inputs cannot be
    converted (defensive against bypassed validation); in that case we skip
    the placeholder entirely and let the post-run refresh discover the row.
    '''
    predicted_name = derive_study_name(form)
    previous_studies = page._studies
    previous_selected = page._selected_study
    previous_running_name = page._running_study_name

    if predicted_name:
        placeholder = StudySummary(
            name=predicted_name,
            pair=form.pair,
            strategy=form.strategy,
            trial_count=0,
            best_is=None,
            direction=StudyDirection.MAXIMIZE,
        )
        page._studies = [placeholder] + [
            s for s in page._studies if s.name != predicted_name
        ]
        page._selected_study = placeholder
        page._running_study_name = predicted_name

    splits = split_trials(form.n_trials, form.n_workers)
    try:
        task = page.phase_mutex.start(
            'is',
            start_in_sample(
                form.pair,
                form.strategy,
                form.start,
                form.end,
                form.n_trials,
                form.n_workers,
                page.job_repo,
                page.is_panel.on_progress,
            )
        )
    except RuntimeError as e:
        page._studies = previous_studies
        page._selected_study = previous_selected
        page._running_study_name = previous_running_name
        ui.notify(str(e), type='negative')
        return

    page._rerender_all()
    page.is_panel.seed_strip(splits)

    try:
        await task
    except asyncio.CancelledError:
        ui.notify('In-sample run cancelled.', type='warning')
    except Exception as e:
        ui.notify(f'In-sample run failed: {e}', type='negative')
