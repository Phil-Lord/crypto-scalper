import pytest

from ui.pages.walk_forward.components.worker_strip import WorkerStrip
from ui.pages.walk_forward.components.worker_tile import WorkerTileState


@pytest.fixture
def strip(mocker) -> WorkerStrip:
    '''
    Return a ``WorkerStrip`` with state initialised but :meth:`_render`
    patched to a no-op, so tests exercise the state machine without a
    NiceGUI client context.
    '''
    instance = WorkerStrip.__new__(WorkerStrip)
    instance._container = mocker.MagicMock()
    instance._states = []
    mocker.patch.object(instance, '_render')
    return instance


@pytest.mark.ui
@pytest.mark.walk_forward_worker_strip
class TestShowWorkers:
    def test_seeds_one_pending_tile_per_worker(self, strip: WorkerStrip):
        strip.show_workers([3, 2, 4])

        assert len(strip._states) == 3
        for state in strip._states:
            assert state.status == 'pending'
            assert state.latest_trial is None
            assert state.best_value is None
            assert state.trials_done == 0

    def test_uses_one_based_worker_ids(self, strip: WorkerStrip):
        '''
        Worker tiles are labelled ``worker 1`` / ``worker 2`` etc. — keeping
        the display id 1-based so the strip aligns with how Optuna numbers
        its workers in logs and progress lines.
        '''
        strip.show_workers([5, 5, 5])
        assert [s.worker_id for s in strip._states] == [1, 2, 3]

    def test_carries_total_trials_per_worker(self, strip: WorkerStrip):
        strip.show_workers([3, 2, 4])
        assert [s.total_trials for s in strip._states] == [3, 2, 4]

    def test_replaces_prior_state(self, strip: WorkerStrip):
        '''
        Seeding mid-strip (e.g. after a previous run) must wipe the old
        states rather than append, so tile counts always match the new run.
        '''
        strip.show_workers([3, 3])
        strip.show_workers([2])

        assert len(strip._states) == 1
        assert strip._states[0].total_trials == 2

    def test_empty_input_leaves_strip_idle(self, strip: WorkerStrip):
        ''' An empty splits list is the equivalent of :meth:`reset_to_idle`. '''
        strip.show_workers([3, 2])
        strip.show_workers([])
        assert strip._states == []

    def test_re_renders(self, strip: WorkerStrip):
        strip.show_workers([2, 2])
        strip._render.assert_called_once()


@pytest.mark.ui
@pytest.mark.walk_forward_worker_strip
class TestOnEvent:
    def test_progress_flips_status_and_updates_fields(self, strip: WorkerStrip):
        # Given
        strip.show_workers([5, 5])
        strip._render.reset_mock()

        # When
        strip.on_event(0, {'event': 'PROGRESS', 'payload': {'trial': 7, 'best': 1.4}})

        # Then
        first = strip._states[0]
        assert first.status == 'running'
        assert first.latest_trial == 7
        assert first.best_value == 1.4
        assert first.trials_done == 1

    def test_done_flips_status_to_done(self, strip: WorkerStrip):
        strip.show_workers([2])
        strip.on_event(0, {'event': 'PROGRESS', 'payload': {'trial': 1, 'best': 0.9}})
        strip.on_event(0, {'event': 'DONE', 'payload': {}})

        assert strip._states[0].status == 'done'

    def test_progress_only_updates_addressed_worker(self, strip: WorkerStrip):
        strip.show_workers([3, 3])
        strip.on_event(1, {'event': 'PROGRESS', 'payload': {'trial': 2, 'best': 0.5}})

        assert strip._states[0].status == 'pending'
        assert strip._states[1].status == 'running'

    @pytest.mark.parametrize('worker_index', [-1, 2, 99])
    def test_out_of_range_worker_index_is_silently_ignored(
        self, strip: WorkerStrip, worker_index: int,
    ):
        '''
        Late events from a worker that has been wiped from the strip (e.g.
        after a reset) must not raise, otherwise the IS panel's
        ``on_progress`` callback would surface tracebacks instead of just
        dropping the event.
        '''
        strip.show_workers([2, 2])
        strip._render.reset_mock()

        strip.on_event(
            worker_index, {'event': 'PROGRESS', 'payload': {'trial': 0, 'best': 0.1}}
        )

        assert strip._render.call_count == 0
        assert all(s.status == 'pending' for s in strip._states)

    def test_unknown_event_kind_is_ignored(self, strip: WorkerStrip):
        ''' Unknown ``event`` values must not raise or re-render. '''
        strip.show_workers([2])
        strip._render.reset_mock()

        strip.on_event(0, {'event': 'BOGUS', 'payload': {}})

        assert strip._render.call_count == 0
        assert strip._states[0].status == 'pending'

    def test_event_re_renders_on_apply(self, strip: WorkerStrip):
        strip.show_workers([2])
        strip._render.reset_mock()

        strip.on_event(0, {'event': 'PROGRESS', 'payload': {'trial': 0, 'best': 0.1}})
        assert strip._render.call_count == 1


@pytest.mark.ui
@pytest.mark.walk_forward_worker_strip
class TestResetToIdle:
    def test_clears_state_and_re_renders(self, strip: WorkerStrip):
        strip.show_workers([2, 2])
        strip._render.reset_mock()

        strip.reset_to_idle()

        assert strip._states == []
        strip._render.assert_called_once()

    def test_idle_strip_resets_cleanly(self, strip: WorkerStrip):
        ''' Calling ``reset_to_idle`` on an already-idle strip is a no-op-ish refresh. '''
        strip.reset_to_idle()
        assert strip._states == []

    def test_does_not_preserve_terminal_tiles(self, strip: WorkerStrip):
        '''
        ``reset_to_idle`` is the strip's only cleanup hook used by the IS
        panel (on a failed run start). It must drop *every* tile so the
        next render shows the empty-state placeholder, not the previous
        run's frozen ``done`` tiles.
        '''
        strip.show_workers([1])
        strip.on_event(0, {'event': 'DONE', 'payload': {}})
        assert strip._states[0].status == 'done'

        strip.reset_to_idle()
        assert strip._states == []


@pytest.mark.ui
@pytest.mark.walk_forward_worker_strip
class TestStatePersistsAcrossEvents:
    def test_progress_then_done_keeps_best_and_trial(self, strip: WorkerStrip):
        '''
        ``apply_done`` must not blow away the worker's best value or last
        trial number — those are still shown on the tile after the worker
        finishes. Covered for the tile in ``test_worker_tile.py``; this
        test pins the strip-level integration.
        '''
        strip.show_workers([2])
        strip.on_event(0, {'event': 'PROGRESS', 'payload': {'trial': 5, 'best': 0.9}})
        strip.on_event(0, {'event': 'PROGRESS', 'payload': {'trial': 6, 'best': 1.1}})
        strip.on_event(0, {'event': 'DONE', 'payload': {}})

        final = strip._states[0]
        assert isinstance(final, WorkerTileState)
        assert final.status == 'done'
        assert final.latest_trial == 6
        assert final.best_value == 1.1
        assert final.trials_done == 2
