'''
Single horizontally-scrolling row of :func:`WorkerTile`s.

Mounts once into the IS panel. The panel calls :meth:`show_workers` when a
run begins and feeds per-worker events through :meth:`on_event` (matching
``start_in_sample``'s ``on_progress`` signature). Tile cleanup at run-end
is handled by the page re-rendering the IS panel on phase done, which
rebuilds a fresh idle strip; :meth:`reset_to_idle` is only used when the
panel itself needs to roll back a failed run start.

The OOS phase has a single-process callback, not per-worker, and is not
wired into this component.
'''
from nicegui import ui

from core import DONE, PROGRESS, StreamEvent
from ui.theme import BORDER, MINOR_HEADER_CLASSES, MUTED_TEXT_CLASSES, StatusPill, separator

from .worker_tile import WorkerTile, WorkerTileState, apply_done, apply_progress


class WorkerStrip:
    '''
    Stateful container for the IS panel's worker tiles.

    Idle by default — renders an empty-state placeholder
    until :meth:`show_workers` is called.

    Re-renders the tile row in place on each state change.
    '''

    def __init__(self) -> None:
        self._container = ui.column().classes('w-full gap-0 min-w-0')
        self._states: list[WorkerTileState] = []
        self._render()

    def show_workers(self, trials_per_worker: list[int]) -> None:
        '''
        Seed one ``pending`` tile per worker and render them.

        Replaces any prior state, so the strip is safe to call at the start
        of every run without a separate reset.

        :param trials_per_worker: Trials allocated to each worker, in
            worker-index order. Must be non-empty; an empty list is
            equivalent to :meth:`reset_to_idle`.
        '''
        self._states = [
            WorkerTileState(
                worker_id=index + 1,
                status='pending',
                latest_trial=None,
                best_value=None,
                trials_done=0,
                total_trials=total,
            )
            for index, total in enumerate(trials_per_worker)
        ]
        self._render()

    def on_event(self, worker_index: int, event: StreamEvent) -> None:
        '''
        Apply one parsed PROGRESS / DONE event from ``start_in_sample``.

        Out-of-range ``worker_index`` values and unknown event kinds are
        ignored — late events arriving after a reset must not raise.
        '''
        if not 0 <= worker_index < len(self._states):
            return
        state = self._states[worker_index]
        if event.event == PROGRESS:
            self._states[worker_index] = apply_progress(state, event.payload)
        elif event.event == DONE:
            self._states[worker_index] = apply_done(state)
        else:
            return
        self._render()

    def reset_to_idle(self) -> None:
        ''' Drop all tiles and re-render the empty-state placeholder. '''
        self._states = []
        self._render()

    def _render(self) -> None:
        self._container.clear()
        with self._container:
            self._render_header()
            if not self._states:
                self._render_idle_placeholder()
            else:
                self._render_tiles()

    def _render_header(self) -> None:
        idle = not self._states
        with ui.row().classes('w-full items-center gap-2 no-wrap mb-2'):
            count_text = '—' if idle else str(len(self._states))
            ui.label(f'WORKERS · {count_text}').classes(MINOR_HEADER_CLASSES)
            separator()
            if not idle and any(s.status == 'running' for s in self._states):
                StatusPill('running', 'LIVE')

    def _render_idle_placeholder(self) -> None:
        with ui.element('div').classes(
            'w-full h-20 flex items-center justify-center '
            f'border border-dashed {BORDER} rounded {MUTED_TEXT_CLASSES}'
        ):
            ui.label('No worker activity — start an in-sample run.')

    def _render_tiles(self) -> None:
        with ui.row().classes(
            'w-full flex-nowrap gap-2 overflow-x-auto pb-1'
        ):
            for state in self._states:
                WorkerTile(state)
