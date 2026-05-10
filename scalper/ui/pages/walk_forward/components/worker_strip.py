'''
Single horizontally-scrolling row of :func:`WorkerTile`s.

Mounts once into the IS panel. The panel calls :meth:`show_workers` when a
run begins, feeds per-worker events through :meth:`on_event` (matching
``start_in_sample``'s ``on_progress`` signature), and calls
:meth:`reset_to_idle` when the run finishes — success, error, or cancel —
so stale tiles never linger.

The OOS phase has a single-process callback, not per-worker, and is not
wired into this component.
'''
from nicegui import ui

from ui.theme import PillStatus, StatusPill

from .worker_tile import WorkerTile, WorkerTileState, apply_done, apply_progress


_TERMINAL_STATUSES: tuple[PillStatus, ...] = ('done', 'error', 'cancelled')


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

    @property
    def states(self) -> list[WorkerTileState]:
        ''' Snapshot of the current tile states (defensive copy). '''
        return list(self._states)

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

    def on_event(self, worker_index: int, event: dict) -> None:
        '''
        Apply one parsed PROGRESS / DONE event from ``start_in_sample``.

        ``event`` matches the contract in ``ui.services.walk_forward``:
        ``{'event': 'PROGRESS' | 'DONE', 'payload': dict}``. Out-of-range
        ``worker_index`` values and unknown event kinds are ignored — late
        events arriving after a reset must not raise.
        '''
        if not 0 <= worker_index < len(self._states):
            return
        state = self._states[worker_index]
        kind = event.get('event')
        payload = event.get('payload', {})
        if kind == 'PROGRESS':
            self._states[worker_index] = apply_progress(state, payload)
        elif kind == 'DONE':
            self._states[worker_index] = apply_done(state)
        else:
            return
        self._render()

    def mark_pending_as(self, status: PillStatus) -> None:
        '''
        Bulk-set every non-terminal tile to ``status``.

        Used by the IS panel when the run is cancelled or fails after some
        workers have already finished — the still-running and pending tiles
        get a final pill state without overwriting workers that already
        reached ``done``.

        :param status: One of ``error`` / ``cancelled``. Other values are
            accepted for completeness but the panel only uses these two.
        '''
        if status not in ('pending', 'running', 'done', 'error', 'cancelled'):
            raise ValueError(
                f'Unknown WorkerStrip status {status!r}; '
                f"expected one of 'pending', 'running', 'done', 'error', 'cancelled'"
            )
        changed = False
        for index, state in enumerate(self._states):
            if state.status in _TERMINAL_STATUSES:
                continue
            self._states[index] = WorkerTileState(
                worker_id=state.worker_id,
                status=status,
                latest_trial=state.latest_trial,
                best_value=state.best_value,
                trials_done=state.trials_done,
                total_trials=state.total_trials
            )
            changed = True
        if changed:
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
            ui.label(f'WORKERS · {count_text}').classes(
                'text-[11px] uppercase tracking-wider text-neutral-400 font-semibold'
            )
            ui.element('div').classes('flex-1 h-px bg-neutral-800')
            if not idle and any(s.status == 'running' for s in self._states):
                StatusPill('running', 'LIVE')

    def _render_idle_placeholder(self) -> None:
        with ui.element('div').classes(
            'w-full h-20 flex items-center justify-center '
            'border border-dashed border-neutral-800 rounded text-xs text-neutral-500'
        ):
            ui.label('No worker activity — start an in-sample run.')

    def _render_tiles(self) -> None:
        with ui.row().classes(
            'w-full flex-nowrap gap-2 overflow-x-auto pb-1'
        ):
            for state in self._states:
                WorkerTile(state)
