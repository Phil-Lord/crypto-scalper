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
import asyncio

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


# Live IS-run refresh cadence. Each tick re-reads the running study's
# trials from Postgres, so the interval is deliberately long.
LIVE_REFRESH_INTERVAL_S = 30.0


class WalkForwardPage:
    '''
    Walk-forward page shell.

    Construction builds the static layout and empty containers synchronously;
    :meth:`mount` then loads the study list off the event loop and renders the
    data-dependent regions. The blocking Optuna/DB reads all run on NiceGUI's
    thread pool (via the ``async`` service helpers), so a large study never
    stalls the single UI event loop and drops the websocket.
    '''

    def __init__(self) -> None:
        ui.dark_mode().enable()
        ui.query('.nicegui-content').classes('p-0 gap-0')  # Remove padding/gap from main content
        ui.query('body').style('overflow: hidden')  # Prevent page scrolling

        # Captured for the background-render guard: timer ticks and the
        # phase-done refresh run after awaits, by which point the client
        # may have disconnected. ``_can_render`` gates UI mutation on it.
        self.client = ui.context.client
        self._mounted = False
        self._phase_refresh_task: asyncio.Task | None = None

        client = SQLAlchemyClient()
        self.job_repo = SQLAlchemyJobRepository(client)
        self.oos_repo = SQLAlchemyOutOfSampleEvaluationRepository(client)

        self.phase_mutex = PhaseMutex()
        self.phase_mutex.subscribe(self._on_phase_change)

        # Studies are loaded in ``mount`` (off the event loop), not here.
        self._studies: list[StudySummary] = []
        self._selected_study: StudySummary | None = None
        self._running_study_name: str | None = None

        self.is_panel = IsPanel(
            phase_mutex=self.phase_mutex,
            get_selected_study=lambda: self._selected_study,
            job_repo=self.job_repo,
            set_running_study_name=self._set_running_study_name,
            is_connected=self._can_render,
        )
        self.oos_panel = OosPanel(
            phase_mutex=self.phase_mutex,
            get_selected_study=lambda: self._selected_study,
            oos_repo=self.oos_repo,
            job_repo=self.job_repo,
            set_running_study_name=self._set_running_study_name,
            is_connected=self._can_render,
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

    async def mount(self) -> None:
        '''
        Load the study list off the event loop and render the data-dependent
        regions. Called once by the page function after construction.
        '''
        self._studies = await rail.load_studies()
        self._selected_study = self._studies[0] if self._studies else None
        await self._rerender_all()
        self._mounted = True

    def _can_render(self) -> bool:
        '''
        ``True`` while it is safe to mutate this page's elements: during the
        initial build (before the socket connects) and whenever the client is
        connected. ``False`` only once a mounted page's client has gone, so
        background renders after a disconnect bail instead of throwing
        ``The client this element belongs to has been deleted.``.
        '''
        return not self._mounted or self.client.has_socket_connection

    async def _rerender_all(self) -> None:
        '''
        Re-render the four regions that read selection or study-list state —
        rail rows, context strip, IS panel, OOS panel. Called from selection
        and study-list mutations (study select, new-study launch, rail refresh).

        Not used by ``_on_phase_change``: a phase transition re-renders only
        the rail, since rebuilding the IS/OOS panels mid-run would discard
        live worker-tile and progress state.
        '''
        if not self._can_render():
            return
        rail.render_rail_rows(self)
        context_strip.render_context_strip(self)
        self.is_panel.render(self._is_row)
        await self.oos_panel.reload()

    def _set_running_study_name(self, name: str | None) -> None:
        self._running_study_name = name

    async def _on_new_study(self) -> None:
        await new_study.on_new_study(self)

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

        Runs synchronously as a mutex listener. The phase-done rail reload now
        hits storage, so it is offloaded onto a background task
        (``_phase_refresh_task``) rather than blocking the notify. Bails early
        if the client has gone — a run can outlive its page.
        '''
        if not self._can_render():
            return
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
            self.new_study_button.enable()
            # Held on self so the task isn't garbage-collected mid-flight.
            self._phase_refresh_task = asyncio.create_task(rail.refresh_rail(self))

    async def _on_live_tick(self) -> None:
        '''
        Per-tick callback for ``_live_timer``. Refreshes the OOS panel
        (windows + top trials) so trials produced by the in-flight IS run
        surface without a manual refresh. Defensive guard against a stray
        tick after deactivation: only fires while IS is the active phase.

        ``OosPanel.refresh`` busts the study cache for the selected study
        before re-reading, so ``get_top_trials_with_oos`` sees the trials the
        IS workers have persisted since the last tick. Those reads offload off
        the event loop, so a 4000-trial study no longer blocks the tick.
        '''
        if not self.phase_mutex.is_active('is'):
            return
        if not self._can_render():
            return
        await self.oos_panel.refresh()


@ui.page('/walk-forward')
async def walk_forward_page() -> None:
    page = WalkForwardPage()
    await page.mount()
