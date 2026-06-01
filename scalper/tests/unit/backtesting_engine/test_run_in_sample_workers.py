import pytest

from backtesting_engine.in_sample_evaluation import (
    _SCALPER_DIR,
    run_in_sample_workers,
    split_trials,
)


def _make_proc(mocker, running: bool = False, rc: int = 0, wait_raises=None):
    '''
    Build a fake ``subprocess.Popen``. ``poll`` reports ``None`` while running;
    a bare ``wait()`` returns ``rc`` (or raises ``wait_raises``), while a
    ``wait(timeout=...)`` from the terminate path always returns ``rc``.
    '''
    proc = mocker.Mock()
    proc.poll.return_value = None if running else rc

    def wait(timeout=None):
        if timeout is None and wait_raises is not None:
            raise wait_raises
        return rc

    proc.wait.side_effect = wait
    return proc


@pytest.mark.backtesting_engine
@pytest.mark.in_sample_evaluation
class TestRunInSampleWorkers:
    def test_spawns_one_subprocess_per_split_from_the_scalper_dir(self, mocker):
        # Given
        procs = [_make_proc(mocker) for _ in range(3)]
        popen = mocker.patch(
            'backtesting_engine.in_sample_evaluation.subprocess.Popen',
            side_effect=procs,
        )

        # When — 10 trials over 3 workers -> [4, 3, 3].
        run_in_sample_workers('BTCGBP', 'SmaStrategy', 1.0, 2.0, n_trials=10, n_workers=3)

        # Then — one Popen per split, each spawned from the scalper dir.
        assert popen.call_count == 3
        for call in popen.call_args_list:
            assert call.kwargs['cwd'] == str(_SCALPER_DIR)
        for proc in procs:
            proc.wait.assert_called()

    def test_split_trial_counts_reach_each_worker_command(self, mocker):
        # Given
        procs = [_make_proc(mocker) for _ in range(3)]
        mocker.patch(
            'backtesting_engine.in_sample_evaluation.subprocess.Popen',
            side_effect=procs,
        )
        build = mocker.patch(
            'backtesting_engine.in_sample_evaluation.build_in_sample_command',
            return_value=['cmd'],
        )

        # When
        run_in_sample_workers('BTCGBP', 'SmaStrategy', 1.0, 2.0, n_trials=10, n_workers=3)

        # Then — each worker got its slice of the split.
        per_worker_trials = [call.args[4] for call in build.call_args_list]
        assert per_worker_trials == [4, 3, 3]

    def test_raises_when_a_worker_exits_non_zero(self, mocker):
        # Given — second worker fails.
        procs = [_make_proc(mocker, rc=0), _make_proc(mocker, rc=1)]
        mocker.patch(
            'backtesting_engine.in_sample_evaluation.subprocess.Popen',
            side_effect=procs,
        )

        # When / Then
        with pytest.raises(RuntimeError, match='exited non-zero'):
            run_in_sample_workers('BTCGBP', 'SmaStrategy', 1.0, 2.0, n_trials=4, n_workers=2)

    def test_keyboard_interrupt_terminates_all_survivors(self, mocker):
        # Given — the first wait() is interrupted (Ctrl+C); both workers still running.
        procs = [
            _make_proc(mocker, running=True, wait_raises=KeyboardInterrupt),
            _make_proc(mocker, running=True),
        ]
        mocker.patch(
            'backtesting_engine.in_sample_evaluation.subprocess.Popen',
            side_effect=procs,
        )

        # When / Then — interrupt propagates and every survivor is terminated.
        with pytest.raises(KeyboardInterrupt):
            run_in_sample_workers('BTCGBP', 'SmaStrategy', 1.0, 2.0, n_trials=4, n_workers=2)
        for proc in procs:
            proc.terminate.assert_called_once()


@pytest.mark.backtesting_engine
@pytest.mark.in_sample_evaluation
class TestSplitTrials:
    def test_splits_evenly(self):
        assert split_trials(10, 5) == [2, 2, 2, 2, 2]

    def test_distributes_remainder_to_first_workers(self):
        assert split_trials(11, 4) == [3, 3, 3, 2]

    def test_drops_workers_that_would_get_zero_trials(self):
        assert split_trials(3, 8) == [1, 1, 1]

    def test_zero_trials_returns_empty(self):
        assert split_trials(0, 4) == []

    def test_zero_workers_returns_empty(self):
        assert split_trials(10, 0) == []
