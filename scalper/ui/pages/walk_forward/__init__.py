'''
Walk-forward UI page (``/walk-forward``).

Studies rail on the left, single detail panel on the right.
The detail panel hosts the in-sample and out-of-sample sections;
this shell renders empty placeholders that WF6/WF7 fill in.

Constructs a single :class:`SQLAlchemyClient` for the page and shares it across
the job and out-of-sample-evaluation repositories so subordinate panels and
service calls can reuse the same connection pool.
'''
import asyncio

from nicegui import ui

from data_system import (
    SQLAlchemyClient,
    SQLAlchemyJobRepository,
    SQLAlchemyOutOfSampleEvaluationRepository,
)
from ui.components import render_header
from ui.models.walk_forward import StudyDirection, StudySummary
from ui.services import list_studies_with_summary, start_in_sample
from ui.theme import SectionTitle, primary_button

from .components import (
    NewStudyForm,
    StatBlock,
    StudyRailRow,
    derive_study_name,
    show_new_study_dialog,
)
from .phase_mutex import PhaseMutex


RAIL_WIDTH_PX = 320


class WalkForwardPage:
    def __init__(self) -> None:
        ui.dark_mode().enable()
        ui.query('.nicegui-content').classes('p-0 gap-0')  # Remove padding/gap from main content
        ui.query('body').style('overflow: hidden')  # Prevent page scrolling

        client = SQLAlchemyClient()
        self.job_repo = SQLAlchemyJobRepository(client)
        self.oos_repo = SQLAlchemyOutOfSampleEvaluationRepository(client)

        self.phase_mutex = PhaseMutex()
        self.phase_mutex.subscribe(self._on_phase_change)

        self._studies: list[StudySummary] = self._load_studies()
        self._selected_study: StudySummary | None = (self._studies[0] if self._studies else None)
        self._running_study_name: str | None = None

        render_header()

        with ui.row().classes('w-full no-wrap gap-0').style('height: calc(100vh - 50px)'):
            self._render_rail()
            self._render_detail()

    def _load_studies(self) -> list[StudySummary]:
        '''
        Fetch studies for the rail.

        Ordered most-recently-active-first by reversing the service's creation-order output,
        so the default selection sits at the top of the rail.
        '''
        try:
            return list(reversed(list_studies_with_summary()))
        except Exception as e:
            ui.notify(f'Could not list studies: {e}', type='negative')
            return []

    def _render_rail(self) -> None:
        with ui.column().classes(
            'h-full border-r border-neutral-800 gap-0 shrink-0'
        ).style(f'width: {RAIL_WIDTH_PX}px'):
            with ui.row().classes(
                'w-full items-baseline justify-between px-4 pt-4 pb-3 no-wrap'
            ):
                ui.label('Studies').classes(
                    'text-sm uppercase tracking-wider text-neutral-300 font-semibold'
                )
                ui.label(str(len(self._studies))).classes(
                    'text-[11px] font-mono text-neutral-500'
                )

            self._rail_list = ui.column().classes(
                'flex-1 min-h-0 w-full gap-0 overflow-y-auto'
            )
            self._render_rail_rows()

            with ui.row().classes(
                'w-full px-4 py-3 border-t border-neutral-800 no-wrap'
            ):
                self.new_study_button = primary_button(
                    '+ NEW STUDY', on_click=self._on_new_study
                )

    def _render_rail_rows(self) -> None:
        self._rail_list.clear()
        with self._rail_list:
            if not self._studies:
                ui.label('No studies yet.').classes('px-4 py-3 text-xs text-neutral-500')
                return
            for study in self._studies:
                is_selected = (
                    self._selected_study is not None
                    and study.name == self._selected_study.name
                )
                is_running = (
                    self.phase_mutex.is_busy
                    and study.name == self._running_study_name
                )
                StudyRailRow(
                    study,
                    active=is_selected,
                    last_run_state='running' if is_running else 'idle',
                    on_click=lambda s=study: self._select_study(s),
                )

    def _render_detail(self) -> None:
        with ui.column().classes('flex-1 min-w-0 h-full gap-0'):
            self._context_strip = ui.row().classes(
                'w-full items-center gap-6 px-6 py-3 border-b border-neutral-800 no-wrap'
            )
            self._render_context_strip()

            self._is_row = ui.column().classes(
                'w-full px-6 py-4 border-b border-neutral-800 gap-2'
            )
            self._oos_row = ui.column().classes(
                'w-full px-6 py-4 flex-1 min-h-0 gap-2'
            )
            self._render_is_placeholder()
            self._render_oos_placeholder()

    def _render_context_strip(self) -> None:
        self._context_strip.clear()
        with self._context_strip:
            study = self._selected_study
            with ui.column().classes('gap-0.5 items-start'):
                ui.label('Selected study').classes(
                    'text-[10px] uppercase tracking-wider text-neutral-500'
                )
                ui.label(study.name if study is not None else '—').classes(
                    'text-[13px] font-mono text-neutral-100'
                )
            ui.element('div').classes('h-8 w-px bg-neutral-800')

            if study is None:
                ui.label('Select or create a study to begin.').classes(
                    'text-xs text-neutral-500'
                )
                return

            StatBlock('Strategy', study.strategy or '—')
            StatBlock('Pair', study.pair or '—')
            StatBlock('Trials', f'{study.trial_count:,}')
            StatBlock(
                'Best IS',
                f'{study.best_is:.3f}' if study.best_is is not None else '—',
                highlight=study.best_is is not None,
            )

    def _render_is_placeholder(self) -> None:
        self._is_row.clear()
        with self._is_row:
            SectionTitle('01', 'IN-SAMPLE')
            ui.label(
                'In-sample optimisation panel.'
                if self._selected_study is not None
                else 'Create a study to enable in-sample optimisation.'
            ).classes('text-xs text-neutral-500')

    def _render_oos_placeholder(self) -> None:
        self._oos_row.clear()
        with self._oos_row:
            SectionTitle('02', 'OUT-OF-SAMPLE')
            ui.label(
                'Out-of-sample evaluation panel.'
                if self._selected_study is not None
                else 'Create a study to enable out-of-sample evaluation.'
            ).classes('text-xs text-neutral-500')

    def _select_study(self, study: StudySummary) -> None:
        if self._selected_study is not None and study.name == self._selected_study.name:
            return
        self._selected_study = study
        self._render_rail_rows()
        self._render_context_strip()
        self._render_is_placeholder()
        self._render_oos_placeholder()

    async def _on_new_study(self) -> None:
        if self.phase_mutex.is_busy:
            return
        form = await show_new_study_dialog()
        if form is None:
            return
        await self._start_in_sample_from_form(form)

    async def _start_in_sample_from_form(self, form: NewStudyForm) -> None:
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
        previous_studies = self._studies
        previous_selected = self._selected_study
        previous_running_name = self._running_study_name

        if predicted_name:
            placeholder = StudySummary(
                name=predicted_name,
                pair=form.pair,
                strategy=form.strategy,
                trial_count=0,
                best_is=None,
                direction=StudyDirection.MAXIMIZE,
            )
            self._studies = [placeholder] + [
                s for s in self._studies if s.name != predicted_name
            ]
            self._selected_study = placeholder
            self._running_study_name = predicted_name

        try:
            task = self.phase_mutex.start(
                'is',
                start_in_sample(
                    form.pair,
                    form.strategy,
                    form.start,
                    form.end,
                    form.n_trials,
                    form.n_workers,
                    self.job_repo
                )
            )
        except RuntimeError as e:
            self._studies = previous_studies
            self._selected_study = previous_selected
            self._running_study_name = previous_running_name
            ui.notify(str(e), type='negative')
            return

        self._render_rail_rows()
        self._render_context_strip()
        self._render_is_placeholder()
        self._render_oos_placeholder()

        try:
            await task
        except asyncio.CancelledError:
            ui.notify('In-sample run cancelled.', type='warning')
        except Exception as e:
            ui.notify(f'In-sample run failed: {e}', type='negative')

    def _refresh_rail(self, select_name: str | None = None) -> None:
        '''
        Reload studies and re-render the rail. When ``select_name`` matches a
        study, that study becomes the selection; otherwise the existing
        selection is preserved if it still exists.
        '''
        self._studies = self._load_studies()
        target_name = select_name or (
            self._selected_study.name if self._selected_study is not None else None
        )
        if target_name is not None:
            match = next((s for s in self._studies if s.name == target_name), None)
            self._selected_study = match if match is not None else (
                self._studies[0] if self._studies else None
            )
        else:
            self._selected_study = self._studies[0] if self._studies else None

        self._render_rail_rows()
        self._render_context_strip()
        self._render_is_placeholder()
        self._render_oos_placeholder()

    def _on_phase_change(self) -> None:
        '''
        Re-render fragments that depend on phase state when the mutex
        changes. Panels (WF6/WF7) read ``phase_mutex`` directly to drive
        their own CTAs and pills.

        The page handles rail-wide concerns:
            - Running / idle pill on the active study's row
            - "+ NEW STUDY" enabledness
            - Full rail reload on phase done so trial counts and best-IS readings catch up.

        No timer — the rail can be stale until phase done
        (live trial counts climb in WF6's worker grid).
        '''
        if self.phase_mutex.is_busy:
            self._render_rail_rows()
            self.new_study_button.disable()
        else:
            self._running_study_name = None
            self._refresh_rail()
            self.new_study_button.enable()


@ui.page('/walk-forward')
def walk_forward_page() -> None:
    WalkForwardPage()
