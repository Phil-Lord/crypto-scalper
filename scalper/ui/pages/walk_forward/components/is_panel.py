'''
In-sample panel for the walk-forward page.

Renders into the page's IS row container, owning the:
    1. Form inputs (trials, workers)
    2. :class:`WorkerStrip`

Reads the rest of its run inputs (pair, strategy, window) off the
selected study because dates are fixed at study creation (rail duty).

The panel never stores its own task. Instead it kicks the in-sample
coroutine off through the page-level :class:`PhaseMutex` and awaits the
returned task only to surface cancel / error notifications. Visual run
state on the worker strip is driven entirely by the ``on_progress``
callback that ``start_in_sample`` already emits per worker.

Re-rendering the panel is destructive (rebuilds the form, drops the
strip's tile state), so the page only re-renders this panel from points
where stale tiles do not matter — initial mount, study selection change,
and the phase-done refresh.
'''
from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd
from nicegui import ui

from data_system import JobRepository
from ui.components import confirm_dialog
from ui.models.walk_forward import StudySummary
from ui.services.walk_forward import split_trials, start_in_sample
from ui.theme import SectionTitle, primary_button, sidebar_input
from utils import get_raw_pair

from ..phase_mutex import PhaseMutex
from .worker_strip import WorkerStrip


_DEFAULT_TRIALS = '100'
_DEFAULT_WORKERS = '4'


@dataclass(frozen=True)
class IsRunInputs:
    '''
    Run inputs reconstructed from a :class:`StudySummary`.

    Attributes:
        raw_pair (str): Pair in the script's input format (e.g. ``'BTCGBP'``).
        strategy (str): Strategy class name.
        start (str): Start datetime in ``'YYYY-M-D-h-m-s'`` text format.
        end (str): End datetime in the same text format.
    '''
    raw_pair: str
    strategy: str
    start: str
    end: str


def derive_run_inputs(study: StudySummary) -> IsRunInputs | None:
    '''
    Decode the inputs needed to extend ``study`` from its name.

    Study names follow ``Strategy_KrakenPair_YYYYMMDD-YYYYMMDD`` (see
    ``backtesting_engine.create_study_name``). Returns ``None`` for legacy or
    hand-renamed studies that don't match, or whose pair isn't in the project
    registry — callers can show a notify error rather than crashing.

    Dates are returned in ``'YYYY-M-D-0-0-0'`` text format because
    ``start_in_sample`` rebuilds the same study name from these inputs and the
    encoded YYYYMMDD has no time-of-day component.
    '''
    parts = study.name.rsplit('_', 2)
    if len(parts) != 3:
        return None
    strategy_part, kraken_pair, window = parts
    try:
        start_str, end_str = window.split('-', 1)
        start_dt = pd.to_datetime(start_str, format='%Y%m%d')
        end_dt = pd.to_datetime(end_str, format='%Y%m%d')
        raw_pair = get_raw_pair(kraken_pair)
    except (ValueError, KeyError):
        return None

    return IsRunInputs(
        raw_pair=raw_pair,
        strategy=strategy_part,
        start=f'{start_dt.year}-{start_dt.month}-{start_dt.day}-0-0-0',
        end=f'{end_dt.year}-{end_dt.month}-{end_dt.day}-0-0-0',
    )


def validate_is_form(n_trials: str | None, n_workers: str | None) -> tuple[int, int]:
    '''
    Coerce raw form values to positive integers, mirroring the new-study
    modal's validation. Raises :class:`ValueError` with a user-facing message.
    '''
    try:
        trials_int = int((n_trials or '').strip())
        workers_int = int((n_workers or '').strip())
    except ValueError:
        raise ValueError('Trials and workers must be integers.')
    if trials_int <= 0 or workers_int <= 0:
        raise ValueError('Trials and workers must be positive.')
    return trials_int, workers_int


class IsPanel:
    '''
    In-sample panel rendered into the IS row of the walk-forward page.

    The panel reads page-level state through injected callables so it never
    needs a back-reference to the page object. ``set_running_study_name`` is
    invoked just before kicking off a run so the rail's running pill latches
    onto the right row during the synchronous mutex notify.

    :param phase_mutex: Page-level mutex; the panel owns the IS coroutine through it.
    :param get_selected_study: Returns the currently selected study or ``None``.
        Read at render time and at run start.
    :param job_repo: Shared SQLAlchemy job repository from the page shell.
    :param set_running_study_name: Page setter for ``_running_study_name``;
        called with the study name on run start, and rolled back to ``None``
        if :meth:`PhaseMutex.start` raises.
    '''

    def __init__(
        self,
        phase_mutex: PhaseMutex,
        get_selected_study: Callable[[], StudySummary | None],
        job_repo: JobRepository,
        set_running_study_name: Callable[[str | None], None],
    ) -> None:
        self._phase_mutex = phase_mutex
        self._get_selected_study = get_selected_study
        self._job_repo = job_repo
        self._set_running_study_name = set_running_study_name
        self._strip: WorkerStrip | None = None
        self._trials_input: ui.input | None = None
        self._workers_input: ui.input | None = None

    def render(self, container: ui.column) -> None:
        '''
        Rebuild the panel into ``container``, replacing any prior content.

        Idempotent — the page calls this on initial mount and again on every
        study selection change and phase-done refresh.
        '''
        container.clear()
        with container:
            self._render_header()
            with ui.row().classes('w-full no-wrap gap-7 items-start'):
                with ui.column().classes('w-64 shrink-0 gap-2'):
                    self._render_sidebar()
                with ui.column().classes('flex-1 min-w-0 gap-0'):
                    self._strip = WorkerStrip()

    def on_progress(self, worker_index: int, event: dict) -> None:
        '''
        Forward a parsed PROGRESS / DONE event into the worker strip.

        Public so the new-study modal flow on the page can wire its
        ``start_in_sample`` call into the same strip without poking the
        panel's internals — useful because that flow does not go through
        :meth:`_on_start`.
        '''
        if self._strip is not None:
            self._strip.on_event(worker_index, event)

    def seed_strip(self, trials_per_worker: list[int]) -> None:
        '''
        Populate the worker strip with one ``pending`` tile per worker.

        Called by the page just after re-rendering the panel for a modal-
        initiated run, so the tiles are in place before the first PROGRESS
        event arrives. Internal to :meth:`_on_start` this happens inline.
        '''
        if self._strip is not None:
            self._strip.show_workers(trials_per_worker)

    def _render_header(self) -> None:
        running = self._phase_mutex.is_active('is')
        SectionTitle(
            '01', 'IN-SAMPLE',
            pill=('running', 'LIVE') if running else None,
        )

    def _render_sidebar(self) -> None:
        study = self._get_selected_study()
        if study is None:
            ui.label('Select or create a study to extend.').classes(
                'text-xs text-neutral-500'
            )
            return

        inputs = derive_run_inputs(study)
        with ui.column().classes('gap-0.5'):
            ui.label('Window').classes(
                'text-[10px] uppercase tracking-wider text-neutral-500'
            )
            ui.label(_format_window(inputs)).classes(
                'text-[12px] font-mono text-neutral-300'
            )

        with ui.row().classes('w-full no-wrap gap-2'):
            self._trials_input = sidebar_input('+ Trials', _DEFAULT_TRIALS)
            self._workers_input = sidebar_input('Workers', _DEFAULT_WORKERS)

        running = self._phase_mutex.is_active('is')
        oos_running = self._phase_mutex.is_other_active('is')
        if running:
            ui.button('■ STOP', on_click=self._on_stop, color='red-9').classes(
                'w-full text-white'
            )
        else:
            button = primary_button('▶ ADD TRIALS', on_click=self._on_start)
            if oos_running or inputs is None:
                button.disable()

    async def _on_start(self) -> None:
        study = self._get_selected_study()
        if study is None:
            return
        if self._phase_mutex.is_busy:
            return  # Button disabled in this state, defensive guard

        inputs = derive_run_inputs(study)
        if inputs is None:
            ui.notify(
                f'Cannot extend {study.name!r}: study name does not match '
                f'the canonical Strategy_Pair_YYYYMMDD-YYYYMMDD format.',
                type='negative',
            )
            return

        try:
            n_trials, n_workers = validate_is_form(
                self._trials_input.value if self._trials_input is not None else None,
                self._workers_input.value if self._workers_input is not None else None,
            )
        except ValueError as e:
            ui.notify(str(e), type='negative')
            return

        splits = split_trials(n_trials, n_workers)
        if not splits:
            ui.notify('No workers to run — check trials and workers.', type='negative')
            return

        strip = self._strip
        if strip is not None:
            strip.show_workers(splits)

        # Set the running study name *before* mutex.start so the synchronous
        # phase-change notify sees the right name when the rail re-renders.
        self._set_running_study_name(study.name)

        on_progress = (
            (lambda i, e, s=strip: s.on_event(i, e)) if strip is not None else None
        )
        try:
            task = self._phase_mutex.start(
                'is',
                start_in_sample(
                    inputs.raw_pair,
                    inputs.strategy,
                    inputs.start,
                    inputs.end,
                    n_trials,
                    n_workers,
                    self._job_repo,
                    on_progress
                )
            )
        except RuntimeError as e:
            self._set_running_study_name(None)
            if strip is not None:
                strip.reset_to_idle()
            ui.notify(str(e), type='negative')
            return

        try:
            await task
        except asyncio.CancelledError:
            ui.notify('In-sample run cancelled.', type='warning')
        except Exception as e:
            ui.notify(f'In-sample run failed: {e}', type='negative')

        # Strip cleanup is the page's job — it re-renders this panel on
        # phase done, which rebuilds the strip in its idle state.

    async def _on_stop(self) -> None:
        if not self._phase_mutex.is_active('is'):
            return
        confirmed = await confirm_dialog(
            title='Stop in-sample run?',
            message='Subprocesses will be terminated. Optuna keeps completed trials.',
            confirm_text='Stop',
        )
        if confirmed:
            self._phase_mutex.cancel()


def _format_window(inputs: IsRunInputs | None) -> str:
    if inputs is None:
        return 'unparseable study name'
    # Drop the '-0-0-0' time suffix for display.
    return f'{inputs.start.removesuffix("-0-0-0")} → {inputs.end.removesuffix("-0-0-0")}'
