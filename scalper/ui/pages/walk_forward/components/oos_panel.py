'''
Out-of-sample panel for the walk-forward page.

Renders into the page's OOS row container, owning the:
    1. Sidebar form (window start/end, top N, workers)
    2. :func:`WindowTabs` strip
    3. Top-N trials table

Reads the selected study via an injected callable, and shares the
page-level :class:`PhaseMutex` and ``OutOfSampleEvaluationRepository``
with the rest of the page. The panel never stores its own task —
it kicks off ``start_out_of_sample`` through the mutex and awaits
the returned task only to surface cancel / error notifications.

Single-subprocess phase: PROGRESS events come *without* a worker index
(unlike IS), so this panel renders ``evaluating trial X of N`` rather
than a worker grid.

Eager params prefetch: on study or window change, the panel calls
``get_trial_params`` for every visible trial and stashes the result keyed
by trial number. The copy button reads the stash so the click is instant
and a prefetch failure on one trial only forces a lazy lookup for that
trial's click — the button stays visible.
'''
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from nicegui import ui

from data_system import (
    JobRepository,
    OosWindowAggregate,
    OutOfSampleEvaluationRepository,
)
from ui.components import confirm_dialog
from ui.models.walk_forward import StudySummary, TrialVerdict, TrialWithOos
from ui.services.walk_forward import (
    get_top_trials_with_oos,
    get_trial_params,
    get_trial_params_bulk,
    invalidate_study_cache,
    list_oos_windows,
    start_out_of_sample,
)
from ui.theme import SectionTitle, StatusPill, primary_button, sidebar_input
from utils import get_second_timestamp, parse_datetime

from ..phase_mutex import PhaseMutex
from .window_tabs import (
    WindowKey,
    WindowTabs,
    auto_select_window,
    format_window_dates
)


logger = logging.getLogger(__name__)


_DEFAULT_START = '2026-1-1-0-0-0'
_DEFAULT_END = '2026-4-1-0-0-0'
_DEFAULT_TOP_N = '25'
_DEFAULT_WORKERS = '4'


@dataclass(frozen=True)
class OosRunInputs:
    '''
    Validated inputs for an OOS run.

    Attributes:
        start (str): Window start in ``'YYYY-M-D-h-m-s'`` text format.
        end (str): Window end in the same format.
        top_n (int): Number of top trials to evaluate.
        n_workers (int): Number of parallel workers inside the subprocess.
    '''
    start: str
    end: str
    top_n: int
    n_workers: int


def validate_oos_form(
    start: str | None,
    end: str | None,
    top_n: str | None,
    n_workers: str | None,
) -> OosRunInputs:
    '''
    Validate the raw OOS form values and return :class:`OosRunInputs`.

    Field rules:

    * ``start`` and ``end`` must be parseable by ``utils.parse_datetime``.
    * ``top_n`` and ``n_workers`` must be positive integers.

    :raises ValueError: With a user-facing message describing the first
        problem encountered.
    '''
    start_text = (start or '').strip()
    end_text = (end or '').strip()
    if not start_text or not end_text:
        raise ValueError('Window start and end are required.')
    try:
        parse_datetime(start_text)
    except ValueError as e:
        raise ValueError(f'Window start is not parseable: {e}')
    try:
        parse_datetime(end_text)
    except ValueError as e:
        raise ValueError(f'Window end is not parseable: {e}')

    try:
        top_n_int = int((top_n or '').strip())
        workers_int = int((n_workers or '').strip())
    except ValueError:
        raise ValueError('Top N and workers must be integers.')
    if top_n_int <= 0 or workers_int <= 0:
        raise ValueError('Top N and workers must be positive.')

    return OosRunInputs(
        start=start_text, end=end_text, top_n=top_n_int, n_workers=workers_int
    )


def derive_window_key(start: str, end: str) -> WindowKey:
    '''
    Convert text-format window dates into a ``(start_ts, end_ts)`` key.

    Used to track the in-flight evaluation's window so its tab wears the
    LIVE pill before any trial has been persisted, and so the trials
    table can swap to it.
    '''
    start_ts = get_second_timestamp(*parse_datetime(start))
    end_ts = get_second_timestamp(*parse_datetime(end))
    return (start_ts, end_ts)


class OosPanel:
    '''
    Out-of-sample panel rendered into the OOS row of the walk-forward page.

    The panel reads page-level state through injected callables so it
    never needs a back-reference to the page object. ``set_running_study_name``
    is invoked just before kicking off a run so the rail's running pill
    latches onto the right row during the synchronous mutex notify.

    :param phase_mutex: Page-level mutex; the panel kicks the OOS
        coroutine off through it.
    :param get_selected_study: Returns the currently selected study or
        ``None``. Read at render time and at run start.
    :param oos_repo: Shared out-of-sample-evaluation repository from the
        page shell. Passed straight into ``list_oos_windows`` /
        ``get_top_trials_with_oos``.
    :param job_repo: Shared SQLAlchemy job repository from the page shell.
    :param set_running_study_name: Page setter for ``_running_study_name``;
        called with the study name on run start, and rolled back to
        ``None`` if :meth:`PhaseMutex.start` raises.
    '''

    def __init__(
        self,
        phase_mutex: PhaseMutex,
        get_selected_study: Callable[[], StudySummary | None],
        oos_repo: OutOfSampleEvaluationRepository,
        job_repo: JobRepository,
        set_running_study_name: Callable[[str | None], None],
    ) -> None:
        self._phase_mutex = phase_mutex
        self._get_selected_study = get_selected_study
        self._oos_repo = oos_repo
        self._job_repo = job_repo
        self._set_running_study_name = set_running_study_name

        self._container: ui.column | None = None
        self._start_input: ui.input | None = None
        self._end_input: ui.input | None = None
        self._top_n_input: ui.input | None = None
        self._workers_input: ui.input | None = None
        self._progress_label: ui.label | None = None

        self._tabs_container: ui.column | None = None
        self._table_container: ui.column | None = None

        self._windows: list[OosWindowAggregate] = []
        self._selected_window: WindowKey | None = None
        self._running_window: WindowKey | None = None
        self._trials: list[TrialWithOos] = []
        self._params_cache: dict[int, dict[str, Any]] = {}
        self._progress_count: int = 0
        self._progress_total: int = 0

    def render(self, container: ui.column) -> None:
        '''
        Rebuild the panel into ``container``, replacing any prior content.

        Idempotent — the page calls this on initial mount and again on
        every study selection change and phase-done refresh. The panel
        itself calls it once on run start so the sidebar flips from
        ``EVALUATE`` to ``STOP``.
        '''
        self._container = container
        container.clear()
        with container:
            self._render_header()
            study = self._get_selected_study()
            if study is None:
                ui.label(
                    'Create a study to enable out-of-sample evaluation.'
                ).classes('text-xs text-neutral-500')
                return
            with ui.row().classes(
                'w-full no-wrap gap-7 items-stretch flex-1 min-h-0'
            ):
                with ui.column().classes('w-64 shrink-0 gap-2'):
                    self._render_sidebar()
                with ui.column().classes('flex-1 min-w-0 gap-3 min-h-0'):
                    # Sidebar inputs exist by the time we get here, so
                    # the data refresh can read top-N off the form.
                    self._refresh_data(study.name)
                    self._render_tabs_section()
                    self._render_table_section()

    def _render_header(self) -> None:
        running = self._phase_mutex.is_active('oos')
        SectionTitle(
            '02', 'OUT-OF-SAMPLE',
            pill=('running', 'LIVE') if running else None,
        )

    def _render_sidebar(self) -> None:
        running = self._phase_mutex.is_active('oos')
        is_running = self._phase_mutex.is_other_active('oos')

        self._start_input = sidebar_input('Window start', _DEFAULT_START)
        self._end_input = sidebar_input('Window end', _DEFAULT_END)
        with ui.row().classes('w-full no-wrap gap-2'):
            self._top_n_input = sidebar_input('Top N', _DEFAULT_TOP_N)
            self._workers_input = sidebar_input('Workers', _DEFAULT_WORKERS)

        if running:
            ui.button(
                '■ STOP', on_click=self._on_stop, color='red-9',
            ).classes('w-full text-white')
            self._progress_label = ui.label(
                self._format_progress()
            ).classes('text-[11px] font-mono text-neutral-400 mt-1')
        else:
            button = primary_button('▶ EVALUATE', on_click=self._on_start)
            if is_running:
                button.disable()
            self._progress_label = None

    def _render_tabs_section(self) -> None:
        with ui.row().classes('w-full items-center gap-2 no-wrap mb-1'):
            ui.label('OOS WINDOWS').classes(
                'text-[11px] uppercase tracking-wider '
                'text-neutral-400 font-semibold'
            )
            ui.element('div').classes('flex-1 h-px bg-neutral-800')
        self._tabs_container = ui.column().classes('w-full gap-0')
        self._render_tabs()

    def _render_tabs(self) -> None:
        if self._tabs_container is None:
            return
        self._tabs_container.clear()
        # Hide the template button while OOS is running — the sidebar
        # inputs are unmounted during a run (replaced by STOP + progress)
        # so there is nowhere to populate.
        on_use_as_template: Callable[[WindowKey], None] | None
        if self._phase_mutex.is_active('oos'):
            on_use_as_template = None
        else:
            on_use_as_template = self._on_use_as_template
        with self._tabs_container:
            WindowTabs(
                self._windows,
                self._selected_window,
                self._effective_running_window(),
                on_select=self._on_select_window,
                on_use_as_template=on_use_as_template,
            )

    def _on_use_as_template(self, key: WindowKey) -> None:
        '''
        Copy the tab's window dates into the sidebar form. Top N and
        workers are left untouched so the user can change them
        independently before clicking EVALUATE.
        '''
        if self._start_input is None or self._end_input is None:
            return
        start_text, end_text = format_window_dates(key)
        self._start_input.value = start_text
        self._end_input.value = end_text

    def _effective_running_window(self) -> WindowKey | None:
        '''
        ``_running_window`` gated on ``phase_mutex.is_active('oos')``.

        The page's phase-done listener re-renders this panel synchronously
        inside ``mutex._on_task_done`` — that fires before ``_on_start``'s
        ``finally`` clears ``_running_window``, so a naive read would
        leave a stale LIVE pill on the just-finished tab. Gating on the
        mutex also makes a study switch mid-run drop the previous study's
        running marker on the new study's tabs.
        '''
        if not self._phase_mutex.is_active('oos'):
            return None
        return self._running_window

    def _render_table_section(self) -> None:
        with ui.row().classes('w-full items-center gap-2 no-wrap mt-2 mb-1'):
            ui.label(self._table_title()).classes(
                'text-[11px] uppercase tracking-wider '
                'text-neutral-400 font-semibold'
            )
            ui.element('div').classes('flex-1 h-px bg-neutral-800')
            ui.button(
                icon='refresh', on_click=self._on_refresh,
            ).props('flat dense round').classes('text-neutral-400')
        self._table_container = ui.column().classes(
            'w-full gap-0 flex-1 min-h-0 overflow-auto'
        )
        self._render_table()

    def _table_title(self) -> str:
        return f'TOP {len(self._trials)} TRIALS' if self._trials else 'TOP TRIALS'

    def _render_table(self) -> None:
        if self._table_container is None:
            return
        self._table_container.clear()
        with self._table_container:
            if not self._trials:
                ui.label(
                    'No top trials yet — extend the study first.'
                ).classes('text-xs text-neutral-500 px-2 py-3')
                return
            self._render_table_header()
            for trial in self._trials:
                self._render_trial_row(trial)

    def _render_table_header(self) -> None:
        with ui.row().classes(
            'w-full items-center px-2 py-1 no-wrap text-[10px] '
            'uppercase tracking-wider text-neutral-500 font-semibold '
            'border-b border-neutral-800'
        ):
            ui.label('Trial').classes('w-16')
            ui.label('IS').classes('w-20 text-right')
            ui.label('OOS').classes('w-20 text-right')
            ui.label('Δ').classes('w-20 text-right')
            ui.label('Verdict').classes('flex-1')
            ui.label('').classes('w-8')

    def _render_trial_row(self, trial: TrialWithOos) -> None:
        with ui.row().classes(
            'w-full items-center px-2 py-1 no-wrap text-[12px] font-mono '
            'border-b border-neutral-800/60'
        ):
            ui.label(f'#{trial.trial_number}').classes('w-16 text-neutral-200')
            ui.label(f'{trial.is_value:.3f}').classes(
                'w-20 text-right text-neutral-200'
            )

            if trial.oos_score is None:
                ui.label('—').classes('w-20 text-right text-neutral-600')
            else:
                colour = (
                    'text-emerald-400' if trial.oos_score >= 0
                    else 'text-red-400'
                )
                ui.label(f'{trial.oos_score:.3f}').classes(
                    f'w-20 text-right {colour}'
                )

            if trial.delta is None:
                ui.label('—').classes('w-20 text-right text-neutral-600')
            else:
                sign = '+' if trial.delta >= 0 else ''
                ui.label(f'{sign}{trial.delta:.3f}').classes(
                    'w-20 text-right text-neutral-300'
                )

            with ui.element('div').classes('flex-1'):
                _render_verdict_pill(trial.verdict)

            ui.button(
                icon='content_copy',
                on_click=lambda _e, t=trial: self._on_copy_params(t),
            ).props('flat dense round').classes('w-8 text-neutral-400')

    async def _on_copy_params(self, trial: TrialWithOos) -> None:
        params = self._params_cache.get(trial.trial_number)
        if params is None:
            study = self._get_selected_study()
            if study is None:
                return
            try:
                params = get_trial_params(study.name, trial.trial_number)
            except Exception as e:
                logger.warning(
                    'Lazy fetch of trial %d params failed: %s',
                    trial.trial_number, e,
                )
                ui.notify('Could not load trial params.', type='negative')
                return
        params_json = json.dumps(params)
        ui.run_javascript(
            f'navigator.clipboard.writeText({json.dumps(params_json)})'
        )
        ui.notify(
            f'Copied params for trial #{trial.trial_number}.',
            type='positive',
        )

    async def _on_refresh(self) -> None:
        study = self._get_selected_study()
        if study is None:
            return
        self._refresh_data(study.name)
        self._render_tabs()
        self._render_table()

    def _refresh_data(self, study_name: str) -> None:
        '''
        Fetch windows, resolve the selected tab, and load + cache the top
        trials for it. Best-effort: errors at any step degrade gracefully
        to an empty section rather than tearing down the panel.

        Drops the module-level Optuna study cache for ``study_name`` so each
        render reads fresh trials. Optuna's ``_CachedStorage`` wraps the
        ``RDBStorage`` the cached :class:`optuna.Study` holds onto, and that
        view can drift across an IS run completing in another process or a
        long-idle UI session — symptom is an empty trials table even though
        trials are visible in the database.
        '''
        invalidate_study_cache(study_name)
        try:
            self._windows = list_oos_windows(study_name, self._oos_repo)
        except Exception as e:
            logger.warning('Failed to list OOS windows for %s: %s', study_name, e)
            self._windows = []

        # Drop selection that no longer maps to a real window (study change
        # or window deleted), unless we are still tracking it as the
        # in-flight run's window.
        running = self._effective_running_window()
        if self._selected_window is not None:
            still_present = any(
                (w.start, w.end) == self._selected_window for w in self._windows
            )
            if not still_present and self._selected_window != running:
                self._selected_window = None

        if self._selected_window is None:
            self._selected_window = auto_select_window(self._windows, running)

        top_n = self._current_top_n()
        try:
            self._trials = get_top_trials_with_oos(
                study_name, self._selected_window, top_n, self._oos_repo,
            )
        except Exception as e:
            logger.warning('Failed to load top trials for %s: %s', study_name, e)
            self._trials = []

        self._refresh_params_cache(study_name)

    def _refresh_params_cache(self, study_name: str) -> None:
        '''
        Eagerly populate the params cache for every visible trial in a
        single pass over the cached Optuna study.

        Bulk-fetch failure falls back to an empty cache; the copy button
        still works via :func:`get_trial_params` on click rather than
        disappearing.
        '''
        if not self._trials:
            self._params_cache = {}
            return
        try:
            self._params_cache = get_trial_params_bulk(
                study_name, (t.trial_number for t in self._trials),
            )
        except Exception as e:
            logger.warning('Failed to prefetch trial params for %s: %s', study_name, e)
            self._params_cache = {}

    def _on_select_window(self, key: WindowKey) -> None:
        if self._selected_window == key:
            return
        self._selected_window = key
        study = self._get_selected_study()
        if study is None:
            return
        top_n = self._current_top_n()
        try:
            self._trials = get_top_trials_with_oos(
                study.name, key, top_n, self._oos_repo,
            )
        except Exception as e:
            logger.warning('Failed to refresh trials on tab click: %s', e)
            self._trials = []
        self._refresh_params_cache(study.name)
        self._render_tabs()
        self._render_table()

    async def _on_start(self) -> None:
        study = self._get_selected_study()
        if study is None:
            return
        if self._phase_mutex.is_busy:
            return  # Button disabled in this state, defensive guard

        try:
            inputs = validate_oos_form(
                self._start_input.value if self._start_input is not None else None,
                self._end_input.value if self._end_input is not None else None,
                self._top_n_input.value if self._top_n_input is not None else None,
                self._workers_input.value if self._workers_input is not None else None
            )
        except ValueError as e:
            ui.notify(str(e), type='negative')
            return

        try:
            window_key = derive_window_key(inputs.start, inputs.end)
        except (ValueError, TypeError) as e:
            ui.notify(f'Could not parse window: {e}', type='negative')
            return

        self._running_window = window_key
        self._selected_window = window_key
        self._progress_count = 0
        self._progress_total = inputs.top_n

        # Set the running study name *before* mutex.start so the synchronous
        # phase-change notify sees the right name when the rail re-renders.
        self._set_running_study_name(study.name)

        try:
            task = self._phase_mutex.start(
                'oos',
                start_out_of_sample(
                    study.name,
                    inputs.top_n,
                    inputs.start,
                    inputs.end,
                    inputs.n_workers,
                    self._job_repo,
                    self._on_progress
                )
            )
        except RuntimeError as e:
            self._set_running_study_name(None)
            self._running_window = None
            ui.notify(str(e), type='negative')
            return

        # Re-render so the sidebar flips to STOP + progress label and the
        # tabs strip shows the running pill on the new window.
        if self._container is not None:
            self.render(self._container)

        try:
            await task
        except asyncio.CancelledError:
            ui.notify('Out-of-sample run cancelled.', type='warning')
        except Exception as e:
            ui.notify(f'Out-of-sample run failed: {e}', type='negative')
        finally:
            self._running_window = None

        # Page's phase-done handler re-renders this panel (via _refresh_rail),
        # which reloads windows + trials and rebuilds the sidebar.

    def _on_progress(self, event: dict) -> None:
        kind = event.get('event')
        if kind == 'PROGRESS':
            self._progress_count += 1
        elif kind == 'DONE':
            self._progress_count = self._progress_total
        else:
            return
        if self._progress_label is not None:
            self._progress_label.set_text(self._format_progress())

    def _format_progress(self) -> str:
        if self._progress_total == 0:
            return 'evaluating…'
        return (
            f'evaluating trial {self._progress_count} of {self._progress_total}'
        )

    async def _on_stop(self) -> None:
        if not self._phase_mutex.is_active('oos'):
            return
        confirmed = await confirm_dialog(
            title='Stop out-of-sample evaluation?',
            message='The subprocess will be terminated and '
                    'all evaluation results will be lost.',
            confirm_text='Stop',
        )
        if confirmed:
            self._phase_mutex.cancel()

    def _current_top_n(self, default: int = 25) -> int:
        if self._top_n_input is None:
            return default
        try:
            value = int((self._top_n_input.value or '').strip())
        except (TypeError, ValueError):
            return default
        return value if value > 0 else default


def _render_verdict_pill(verdict: TrialVerdict) -> None:
    if verdict == TrialVerdict.PENDING:
        StatusPill('pending', 'PENDING')
    elif verdict == TrialVerdict.GENERALISES:
        StatusPill('done', 'GENERALISES')
    else:
        StatusPill('error', 'OVERFIT')
