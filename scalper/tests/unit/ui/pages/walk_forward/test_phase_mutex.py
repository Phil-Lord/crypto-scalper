import asyncio

import pytest

from ui.pages.walk_forward.phase_mutex import PhaseMutex


@pytest.mark.ui
@pytest.mark.walk_forward_phase_mutex
class TestPhaseMutex:
    def test_starts_idle(self):
        mutex = PhaseMutex()

        assert mutex.running is None
        assert mutex.task is None
        assert mutex.is_busy is False
        assert mutex.is_active('is') is False
        assert mutex.is_active('oos') is False
        assert mutex.is_other_active('is') is False
        assert mutex.is_other_active('oos') is False

    def test_start_sets_running_and_task(self):
        async def scenario():
            mutex = PhaseMutex()
            gate = asyncio.Event()

            async def coro():
                await gate.wait()

            task = mutex.start('is', coro())

            assert mutex.running == 'is'
            assert mutex.task is task
            assert mutex.is_busy is True
            assert mutex.is_active('is') is True
            assert mutex.is_other_active('oos') is True
            assert mutex.is_other_active('is') is False

            gate.set()
            await task

        asyncio.run(scenario())

    def test_clears_state_when_task_completes(self):
        async def scenario():
            mutex = PhaseMutex()

            async def coro():
                return None

            task = mutex.start('oos', coro())
            await task

            assert mutex.running is None
            assert mutex.task is None
            assert mutex.is_busy is False

        asyncio.run(scenario())

    def test_clears_state_when_task_raises(self):
        async def scenario():
            mutex = PhaseMutex()

            async def coro():
                raise ValueError('boom')

            task = mutex.start('is', coro())
            with pytest.raises(ValueError, match='boom'):
                await task

            assert mutex.running is None
            assert mutex.task is None

        asyncio.run(scenario())

    def test_start_raises_when_already_running(self):
        async def scenario():
            mutex = PhaseMutex()
            gate = asyncio.Event()

            async def first():
                await gate.wait()

            async def second():
                return None

            first_task = mutex.start('is', first())
            coro_two = second()
            try:
                with pytest.raises(RuntimeError, match="'is' is already running"):
                    mutex.start('oos', coro_two)
            finally:
                coro_two.close()
                gate.set()
                await first_task

        asyncio.run(scenario())

    def test_cancel_cancels_running_task(self):
        async def scenario():
            mutex = PhaseMutex()

            async def coro():
                await asyncio.sleep(60)

            task = mutex.start('is', coro())
            mutex.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

            assert mutex.running is None
            assert mutex.task is None

        asyncio.run(scenario())

    def test_cancel_is_noop_when_idle(self):
        mutex = PhaseMutex()
        mutex.cancel()  # should not raise
        assert mutex.running is None

    def test_can_run_again_after_completion(self):
        async def scenario():
            mutex = PhaseMutex()

            async def coro():
                return None

            await mutex.start('is', coro())
            task = mutex.start('oos', coro())
            await task
            assert mutex.running is None

        asyncio.run(scenario())

    def test_subscribers_notified_on_start_and_finish(self):
        async def scenario():
            mutex = PhaseMutex()
            observed: list[str | None] = []

            def listener():
                observed.append(mutex.running)

            mutex.subscribe(listener)

            async def coro():
                return None

            await mutex.start('is', coro())

            assert observed == ['is', None]

        asyncio.run(scenario())

    def test_multiple_subscribers_all_notified_in_order(self):
        async def scenario():
            mutex = PhaseMutex()
            order: list[str] = []

            mutex.subscribe(lambda: order.append('first'))
            mutex.subscribe(lambda: order.append('second'))

            async def coro():
                return None

            await mutex.start('is', coro())

            assert order == ['first', 'second', 'first', 'second']

        asyncio.run(scenario())
