'''
Page-level mutex for the walk-forward page.

Only one phase (in-sample or out-of-sample) may run at a time across the whole
page. The page owns the mutex and the running task; panels read its state to
decide CTA labels and disabled-ness, but never store their own task.

Generalises the single-flag ``_set_loading`` helper from
``pages/backtesting_engine.py`` into a two-way mutex with subscriber
notifications so dependent UI fragments can re-render on phase change.
'''
from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, Literal


Phase = Literal['is', 'oos']


class PhaseMutex:
    '''
    Tracks which phase, if any, is currently running and owns its task.

    Attributes:
        running (Phase | None): ``'is'`` or ``'oos'`` while a phase is in
            flight, ``None`` otherwise.
        task (asyncio.Task | None): The task wrapping the running coroutine,
            or ``None`` when idle.

    Subscribers registered via :meth:`subscribe` are notified synchronously
    whenever ``running`` changes (start and finish), so panels and the rail
    can re-render against the new state.
    '''

    def __init__(self) -> None:
        self._running: Phase | None = None
        self._task: asyncio.Task[Any] | None = None
        self._listeners: list[Callable[[], None]] = []

    @property
    def running(self) -> Phase | None:
        return self._running

    @property
    def task(self) -> asyncio.Task[Any] | None:
        return self._task

    @property
    def is_busy(self) -> bool:
        return self._running is not None

    def is_active(self, phase: Phase) -> bool:
        '''``True`` if ``phase`` is the one currently running.'''
        return self._running == phase

    def is_other_active(self, phase: Phase) -> bool:
        '''``True`` if a *different* phase from ``phase`` is currently running.'''
        return self._running is not None and self._running != phase

    def subscribe(self, listener: Callable[[], None]) -> None:
        '''
        Register a no-arg callback fired on every phase-state change.

        Listeners run synchronously in registration order. Exceptions raised
        by a listener propagate to the caller of ``start``/``cancel``/the task
        completion path; keep listeners short and side-effect-only.
        '''
        self._listeners.append(listener)

    def start(self, phase: Phase, coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
        '''
        Start ``coro`` under the mutex for ``phase``.

        :raises RuntimeError: If another phase is already running.
        :return: The task wrapping ``coro``. Callers may await it; the mutex
            clears its state when the task completes regardless.
        '''
        if self._running is not None:
            raise RuntimeError(
                f'Cannot start {phase!r}: {self._running!r} is already running'
            )
        self._running = phase
        task = asyncio.create_task(coro)
        task.add_done_callback(self._on_task_done)
        self._task = task
        self._notify()
        return task

    def _on_task_done(self, task: asyncio.Task[Any]) -> None:
        # Done callbacks run in the event loop after the task finishes
        # (success, exception, or cancellation) so this always fires.
        if self._task is not task:
            return  # Stale callback from a superseded run
        self._running = None
        self._task = None
        self._notify()

    def cancel(self) -> None:
        '''
        Request cancellation of the running task, if any.

        No-op when idle. Cancellation propagates through ``asyncio``;
        the mutex clears its state once the task actually finishes.
        '''
        if self._task is not None:
            self._task.cancel()

    def _notify(self) -> None:
        for listener in self._listeners:
            listener()
