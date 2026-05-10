import pytest

from ui.pages.walk_forward.components.worker_tile import (
    WorkerTileState,
    apply_done,
    apply_progress,
)


def _pending(total_trials: int = 10) -> WorkerTileState:
    return WorkerTileState(
        worker_id=1,
        status='pending',
        latest_trial=None,
        best_value=None,
        trials_done=0,
        total_trials=total_trials,
    )


@pytest.mark.ui
@pytest.mark.walk_forward_worker_tile
class TestApplyProgress:
    def test_flips_status_to_running(self):
        result = apply_progress(_pending(), {'trial': 0, 'value': 0.5, 'best': 0.5})
        assert result.status == 'running'

    def test_increments_trials_done(self):
        state = _pending()
        first = apply_progress(state, {'trial': 0, 'best': 0.1})
        second = apply_progress(first, {'trial': 1, 'best': 0.2})
        assert (first.trials_done, second.trials_done) == (1, 2)

    def test_sets_latest_trial_and_best(self):
        result = apply_progress(_pending(), {'trial': 7, 'value': 1.2, 'best': 1.2})
        assert result.latest_trial == 7
        assert result.best_value == 1.2

    def test_keeps_previous_best_when_payload_best_is_none(self):
        '''
        ``optimise_in_sample`` reports ``best=None`` until the first trial
        completes, even on PROGRESS events that arrive after a real best
        reading. Apply must not wipe the previous reading.
        '''
        # Given
        state = apply_progress(_pending(), {'trial': 0, 'best': 0.4})

        # When
        result = apply_progress(state, {'trial': 1, 'best': None})

        # Then
        assert result.best_value == 0.4
        assert result.latest_trial == 1

    def test_keeps_previous_trial_when_payload_trial_missing(self):
        state = apply_progress(_pending(), {'trial': 3, 'best': 0.4})
        result = apply_progress(state, {'best': 0.5})
        assert result.latest_trial == 3

    def test_state_is_immutable(self):
        with pytest.raises((AttributeError, TypeError)):
            _pending().status = 'running'


@pytest.mark.ui
@pytest.mark.walk_forward_worker_tile
class TestApplyDone:
    def test_flips_status_to_done(self):
        running = apply_progress(_pending(), {'trial': 9, 'best': 0.7})
        result = apply_done(running)
        assert result.status == 'done'

    def test_preserves_other_fields(self):
        running = apply_progress(_pending(total_trials=5), {'trial': 4, 'best': 0.7})
        result = apply_done(running)
        assert result.latest_trial == 4
        assert result.best_value == 0.7
        assert result.trials_done == 1
        assert result.total_trials == 5
