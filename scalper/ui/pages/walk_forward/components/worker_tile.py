'''
Single worker tile rendered inside :class:`WorkerStrip`.

Shows the live state of one worker subprocess in an in-sample run. State
transitions are kept as pure functions on the :class:`WorkerTileState`
dataclass so they can be unit-tested without a NiceGUI client context.

No progress bar — the PROGRESS payload from ``optimise_in_sample.py`` does
not include a 0..1 fraction, only the latest trial number and best value.
'''
from dataclasses import dataclass, replace

from nicegui import ui

from ui.theme import PillStatus, StatusPill


@dataclass(frozen=True)
class WorkerTileState:
    '''
    Visible state of a single worker tile.

    Attributes:
        worker_id (int): Display id (1-based).
        status (PillStatus): Pill state.
            - ``pending`` before the first PROGRESS event
            - ``running`` while trials are streaming in
            - ``done`` after the worker emits ``DONE``
            Cancellation and errors are surfaced via a notify and a panel
            re-render that rebuilds the strip in its idle state, so tiles
            never carry an ``error`` / ``cancelled`` status here.
        latest_trial (int | None): Global Optuna trial number from the most
            recent PROGRESS event. ``None`` while the tile is pending.
        best_value (float | None): Worker's best value so far. ``None`` until
            at least one trial has completed (``optimise_in_sample`` reports
            ``best=None`` until then).
        trials_done (int): Number of PROGRESS events received from this
            worker — used to render the ``X of N`` progress caption.
        total_trials (int): Trials allocated to this worker at run start.
    '''
    worker_id: int
    status: PillStatus
    latest_trial: int | None
    best_value: float | None
    trials_done: int
    total_trials: int


def apply_progress(state: WorkerTileState, payload: dict) -> WorkerTileState:
    '''
    Return a new state with the fields from a PROGRESS payload merged in.

    Pure — the strip applies the result back to its internal list.

    :param state: Current tile state.
    :param payload: Inner ``payload`` dict of the parsed event, expected to
        contain ``trial`` (int) and ``best`` (float | None). Missing values
        leave the previous state field untouched so that an early
        ``best=None`` does not wipe a real reading.
    '''
    new_trial = payload.get('trial')
    new_best = payload.get('best')
    return replace(
        state,
        status='running',
        latest_trial=new_trial if new_trial is not None else state.latest_trial,
        best_value=new_best if new_best is not None else state.best_value,
        trials_done=state.trials_done + 1,
    )


def apply_done(state: WorkerTileState) -> WorkerTileState:
    ''' Return a new state with the status flipped to ``done``. '''
    return replace(state, status='done')


def WorkerTile(state: WorkerTileState) -> None:
    '''
    Fixed-width tile showing one worker's progress.

    Layout:

    * Top row — ``worker {id}`` label and a :func:`StatusPill`.
    * Centre — best value (large mono), or ``—`` while pending / before any
        trial has completed.
    * Bottom row — latest trial number (or ``queued`` when pending) on the
        left, ``X of N`` worker-trial counter on the right.
    '''
    pending = state.status == 'pending'
    with ui.column().classes(
        'shrink-0 w-40 px-3 py-2 gap-1 border border-neutral-800 '
        'rounded bg-neutral-900/40'
    ):
        with ui.row().classes('w-full items-center justify-between gap-2 no-wrap'):
            ui.label(f'worker {state.worker_id}').classes(
                'text-[11px] font-mono text-neutral-400'
            )
            StatusPill(state.status)

        best_text = (
            f'{state.best_value:.3f}' if state.best_value is not None else '—'
        )
        best_color = 'text-neutral-600' if state.best_value is None else 'text-neutral-100'
        ui.label(best_text).classes(f'text-base font-mono {best_color}')

        with ui.row().classes('w-full items-center justify-between gap-2 no-wrap'):
            trial_text = (
                'queued' if pending or state.latest_trial is None
                else f'trial {state.latest_trial}'
            )
            ui.label(trial_text).classes('text-[10px] font-mono text-neutral-500')
            ui.label(f'{state.trials_done} of {state.total_trials}').classes(
                'text-[10px] font-mono text-neutral-500'
            )
