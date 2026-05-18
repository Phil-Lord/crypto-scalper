'''
Walk-forward UI page.

Studies rail on the left, single detail panel on the right hosting the
in-sample and out-of-sample sections.

Constructs a single :class:`SQLAlchemyClient` for the page and shares it across
the job and out-of-sample-evaluation repositories so subordinate panels and
service calls can reuse the same connection pool.

The page itself is a thin shell: lifecycle wiring (mutex, live timer, repos)
lives here, while rendering and event handlers are split across sibling
modules — :mod:`.rail`, :mod:`.context_strip`, :mod:`.detail`, :mod:`.new_study`.
'''
from nicegui import ui

from data_system import (
    SQLAlchemyClient,
    SQLAlchemyJobRepository,
    SQLAlchemyOutOfSampleEvaluationRepository,
)
from ui.components import render_header
from ui.services.walk_forward import invalidate_study_cache
from utils import StudySummary

from . import context_strip, detail, new_study, rail
from .components import IsPanel, OosPanel
from .phase_mutex import PhaseMutex


LIVE_REFRESH_INTERVAL_S = 5.0


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

        self._studies: list[StudySummary] = rail.load_studies()
        self._selected_study: StudySummary | None = (self._studies[0] if self._studies else None)
        self._running_study_name: str | None = None

        self.is_panel = IsPanel(
            phase_mutex=self.phase_mutex,
            get_selected_study=lambda: self._selected_study,
            job_repo=self.job_repo,
            set_running_study_name=self._set_running_study_name
        )
        self.oos_panel = OosPanel(
            phase_mutex=self.phase_mutex,
            get_selected_study=lambda: self._selected_study,
            oos_repo=self.oos_repo,
            job_repo=self.job_repo,
            set_running_study_name=self._set_running_study_name
        )

        render_header()

        with ui.row().classes('w-full no-wrap gap-0').style('height: calc(100vh - 50px)'):
            rail.render_rail(self)
            detail.render_detail(self)

        # Live IS refresh timer: ticks while an in-sample run is active so
        # the OOS panel's window list and top-trials table catch up with
        # new trials. Activated/deactivated by ``_on_phase_change``; the
        # rail intentionally does NOT refresh on the timer (only on phase
        # done) since per-trial counts climb in IsPanel's worker grid.
        self._live_timer = ui.timer(LIVE_REFRESH_INTERVAL_S, self._on_live_tick, active=False)

    async def _on_new_study(self) -> None:
        await new_study.on_new_study(self)

    def _set_running_study_name(self, name: str | None) -> None:
        self._running_study_name = name

    def _on_phase_change(self) -> None:
        '''
        Re-render fragments that depend on phase state when the mutex
        changes. Panels (WF6/WF7) read ``phase_mutex`` directly to drive
        their own CTAs and pills.

        The page handles rail-wide concerns:
            - Running / idle pill on the active study's row
            - "+ NEW STUDY" enabledness
            - Full rail reload on phase done so trial counts and best-IS readings catch up.
            - Live OOS-panel refresh timer activated only while IS is running.

        Rail-row trial counts intentionally remain stale until phase done
        (live counts climb in the worker grid), so the timer skips it.
        '''
        if self.phase_mutex.is_busy:
            rail.render_rail_rows(self)
            self.new_study_button.disable()
            if self.phase_mutex.is_active('is'):
                self._live_timer.activate()
            else:
                self._live_timer.deactivate()
        else:
            self._live_timer.deactivate()
            finished_study = self._running_study_name
            self._running_study_name = None
            # Drop the cached Study for the just-finished run so the OOS
            # panel's phase-done re-render reads the trials the worker
            # subprocesses just persisted. Optuna's _CachedStorage view
            # held by the cached Study can otherwise lag the database.
            if finished_study is not None:
                invalidate_study_cache(finished_study)
            rail.refresh_rail(self)
            self.new_study_button.enable()

    def _on_live_tick(self) -> None:
        '''
        Per-tick callback for ``_live_timer``. Refreshes the OOS panel
        (windows + top trials) so trials produced by the in-flight IS run
        surface without a manual refresh. Defensive guard against a stray
        tick after deactivation: only fires while IS is the active phase.

        Invalidates the cached Study for the running run before refreshing
        so ``get_top_trials_with_oos`` sees the trials the IS workers have
        persisted since the last tick.
        '''
        if not self.phase_mutex.is_active('is'):
            return
        if self._running_study_name is not None:
            invalidate_study_cache(self._running_study_name)
        self.oos_panel.refresh()


@ui.page('/walk-forward')
def walk_forward_page() -> None:
    WalkForwardPage()
