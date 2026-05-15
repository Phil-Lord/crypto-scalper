import asyncio
from unittest.mock import MagicMock

import pytest

from data_system.models.oos_window_aggregate_model import OosWindowAggregate
from ui.services import walk_forward as svc
from utils import StudyDirection, StudySummary


@pytest.mark.ui
@pytest.mark.ui_services
@pytest.mark.walk_forward
class TestSplitTrials:
    def test_splits_evenly(self):
        assert svc.split_trials(10, 5) == [2, 2, 2, 2, 2]

    def test_distributes_remainder_to_first_workers(self):
        assert svc.split_trials(11, 4) == [3, 3, 3, 2]

    def test_drops_workers_when_more_workers_than_trials(self):
        assert svc.split_trials(3, 8) == [1, 1, 1]

    def test_returns_empty_when_no_trials(self):
        assert svc.split_trials(0, 4) == []

    def test_returns_empty_when_no_workers(self):
        assert svc.split_trials(10, 0) == []


@pytest.mark.ui
@pytest.mark.ui_services
@pytest.mark.walk_forward
class TestGetTopTrials:
    def test_delegates_to_backtesting_engine_helpers(self, mocker):
        # Given
        study_sentinel = object()
        param_sets_sentinel = [{'trial_number': 1, 'value': 5.0, 'params': {}}]
        load = mocker.patch.object(svc, 'load_study', return_value=study_sentinel)
        get_top = mocker.patch.object(
            svc, 'get_top_param_sets', return_value=param_sets_sentinel,
        )

        # When
        result = svc.get_top_trials('my_study', 2)

        # Then
        load.assert_called_once_with('my_study')
        get_top.assert_called_once_with(study_sentinel, 2)
        assert result is param_sets_sentinel


@pytest.mark.ui
@pytest.mark.ui_services
@pytest.mark.walk_forward
class TestStartInSample:
    def test_creates_one_job_per_worker_and_runs_in_parallel(self, mocker):
        '''
        ``start_in_sample`` should create one ``Job(JobType.OPTIMISE_IN_SAMPLE)``
        per worker and pass the trial-split count through to each subprocess
        command. We mock ``run_subprocess`` so this stays a unit test.
        '''
        from data_system import JobRepository, JobType

        captured: list = []

        async def fake_run_subprocess(
            job_repo, job, cmd, on_progress=None, cwd=None, **kwargs
        ):
            captured.append((job, cmd, cwd))

        mocker.patch.object(svc, 'run_subprocess', side_effect=fake_run_subprocess)
        mock_repo = mocker.MagicMock(spec=JobRepository)

        jobs = asyncio.run(svc.start_in_sample(
            'BTCGBP', 'SmaStrategy', '2025-1-1-0-0-0', '2025-2-1-0-0-0',
            n_trials=10, n_workers=4, job_repo=mock_repo,
        ))

        assert len(jobs) == 4
        assert all(j.job_type == JobType.OPTIMISE_IN_SAMPLE for j in jobs)
        # 10 trials across 4 workers = [3, 3, 2, 2]
        trial_counts = []
        for _, cmd, _ in captured:
            trial_counts.append(int(cmd[cmd.index('-n') + 1]))
        assert sorted(trial_counts) == [2, 2, 3, 3]
        # All run with cwd set to the scalper/ directory.
        assert all(cwd is not None and cwd.endswith('/scalper') for _, _, cwd in captured)

    def test_cancels_sibling_workers_when_one_raises(self, mocker):
        '''
        If one worker raises a non-cancellation exception, the remaining
        workers must be cancelled — otherwise their subprocesses leak as
        orphans. ``asyncio.gather`` does not cancel siblings on its own when
        a child raises (see Python docs), so the service has to.
        '''
        from data_system import JobRepository

        started: list[int] = []
        cancelled: list[int] = []
        completed: list[int] = []
        counter = {'value': 0}

        async def fake_run_subprocess(
            job_repo, job, cmd, on_progress=None, cwd=None, **kwargs
        ):
            my_index = counter['value']
            counter['value'] += 1
            started.append(my_index)
            if my_index == 0:
                # Yield once so siblings reach their sleep before we raise.
                await asyncio.sleep(0)
                raise OSError('cannot spawn')
            try:
                await asyncio.sleep(10)
                completed.append(my_index)
            except asyncio.CancelledError:
                cancelled.append(my_index)
                raise

        mocker.patch.object(svc, 'run_subprocess', side_effect=fake_run_subprocess)
        mock_repo = mocker.MagicMock(spec=JobRepository)

        with pytest.raises(OSError, match='cannot spawn'):
            asyncio.run(svc.start_in_sample(
                'BTCGBP', 'SmaStrategy', '2025-1-1-0-0-0', '2025-2-1-0-0-0',
                n_trials=10, n_workers=4, job_repo=mock_repo,
            ))

        assert started == [0, 1, 2, 3]
        assert sorted(cancelled) == [1, 2, 3]
        assert completed == []

    def test_progress_callback_is_invoked_per_worker_with_parsed_event(self, mocker):
        '''
        Each worker's per-line callback should parse the ``PROGRESS``/``DONE``
        contract and forward ``(worker_index, event)`` to the page-level
        callback. Lines that don't match the contract are dropped.
        '''
        from data_system import JobRepository

        async def fake_run_subprocess(
            job_repo, job, cmd, on_progress=None, cwd=None, **kwargs
        ):
            on_progress('PROGRESS {"trial": 0, "value": 1.0, "best": 1.0}')
            on_progress('not-a-progress-line')
            on_progress('DONE {"trials": 1}')

        mocker.patch.object(svc, 'run_subprocess', side_effect=fake_run_subprocess)
        mock_repo = mocker.MagicMock(spec=JobRepository)
        captured = []

        asyncio.run(svc.start_in_sample(
            'BTCGBP', 'SmaStrategy', '2025-1-1-0-0-0', '2025-2-1-0-0-0',
            n_trials=2, n_workers=2, job_repo=mock_repo,
            on_progress=lambda i, e: captured.append((i, e)),
        ))

        # 2 workers × 2 valid lines each, malformed lines dropped.
        assert len(captured) == 4
        assert all(isinstance(i, int) and 0 <= i < 2 for i, _ in captured)
        assert {e.event for _, e in captured} == {'PROGRESS', 'DONE'}


@pytest.mark.ui
@pytest.mark.ui_services
@pytest.mark.walk_forward
class TestListStudies:
    def test_delegates_to_utils_list_studies(self, mocker):
        sentinel = [StudySummary(
            name='SmaStrategy_BTCGBP_20240101-20240601',
            pair='BTCGBP',
            strategy='SmaStrategy',
            trial_count=10,
            best_is=1.1,
            direction=StudyDirection.MAXIMIZE,
        )]
        loader = mocker.patch.object(
            svc, '_list_studies_from_storage', return_value=sentinel,
        )

        result = svc.list_studies()

        assert result is sentinel
        loader.assert_called_once_with()


@pytest.mark.ui
@pytest.mark.ui_services
@pytest.mark.walk_forward
class TestListOosWindows:
    def test_returns_repo_aggregates(self):
        aggregates = [
            OosWindowAggregate(start=1.0, end=2.0, best_oos=0.9,
                               generalised_count=3, overfit_count=1),
            OosWindowAggregate(start=3.0, end=4.0, best_oos=0.4,
                               generalised_count=0, overfit_count=2),
        ]
        repo = MagicMock()
        repo.aggregate_windows.return_value = aggregates

        result = svc.list_oos_windows('study-x', repo)

        assert result == aggregates
        repo.aggregate_windows.assert_called_once_with(
            'study-x', svc.OOS_OVERFIT_THRESHOLD
        )

    def test_returns_empty_when_repo_returns_no_rows(self):
        repo = MagicMock()
        repo.aggregate_windows.return_value = []

        assert svc.list_oos_windows('empty', repo) == []


@pytest.mark.ui
@pytest.mark.ui_services
@pytest.mark.walk_forward
class TestGetTopTrialsWithOos:
    def test_delegates_to_engine_with_cached_study(self, mocker):
        ''' The service is a thin wrapper that injects the cached study. '''
        study_sentinel = object()
        result_sentinel = [object()]
        load = mocker.patch.object(svc, 'load_study', return_value=study_sentinel)
        engine_fn = mocker.patch.object(
            svc, '_get_top_trials_with_oos_from_engine', return_value=result_sentinel,
        )
        repo = MagicMock()

        result = svc.get_top_trials_with_oos('study-x', (10.0, 20.0), n_trials=5, oos_repo=repo)

        load.assert_called_once_with('study-x')
        engine_fn.assert_called_once_with(study_sentinel, (10.0, 20.0), 5, repo)
        assert result is result_sentinel


@pytest.mark.ui
@pytest.mark.ui_services
@pytest.mark.walk_forward
class TestGetTrialParams:
    def test_returns_params_for_matching_trial(self, mocker):
        trial_a = MagicMock(number=0, params={'a': 1})
        trial_b = MagicMock(number=7, params={'a': 2, 'b': 3})
        study = MagicMock(trials=[trial_a, trial_b])
        mocker.patch.object(svc, 'load_study', return_value=study)

        assert svc.get_trial_params('s', 7) == {'a': 2, 'b': 3}

    def test_raises_keyerror_when_trial_missing(self, mocker):
        study = MagicMock(trials=[MagicMock(number=0)])
        mocker.patch.object(svc, 'load_study', return_value=study)

        with pytest.raises(KeyError, match='Trial 99'):
            svc.get_trial_params('s', 99)

    def test_raises_keyerror_when_study_has_no_trials(self, mocker):
        study = MagicMock(trials=[])
        mocker.patch.object(svc, 'load_study', return_value=study)

        with pytest.raises(KeyError, match='Trial 0'):
            svc.get_trial_params('s', 0)


@pytest.mark.ui
@pytest.mark.ui_services
@pytest.mark.walk_forward
class TestGetTrialParamsBulk:
    def test_returns_params_for_requested_trials_in_single_pass(self, mocker):
        trials = [
            MagicMock(number=0, params={'a': 1}),
            MagicMock(number=7, params={'a': 2}),
            MagicMock(number=9, params={'a': 3}),
        ]
        study = MagicMock(trials=trials)
        load = mocker.patch.object(svc, 'load_study', return_value=study)

        result = svc.get_trial_params_bulk('s', [0, 9])

        assert result == {0: {'a': 1}, 9: {'a': 3}}
        load.assert_called_once_with('s')

    def test_omits_missing_trial_numbers(self, mocker):
        '''
        Missing trial numbers don't raise; the panel falls back to a lazy
        per-click lookup via :func:`get_trial_params` for any number it
        didn't get back.
        '''
        study = MagicMock(trials=[MagicMock(number=0, params={'a': 1})])
        mocker.patch.object(svc, 'load_study', return_value=study)

        assert svc.get_trial_params_bulk('s', [0, 42]) == {0: {'a': 1}}

    def test_empty_input_skips_load_study(self, mocker):
        load = mocker.patch.object(svc, 'load_study')

        assert svc.get_trial_params_bulk('s', []) == {}
        load.assert_not_called()


@pytest.mark.ui
@pytest.mark.ui_services
@pytest.mark.walk_forward
class TestStudyCache:
    def setup_method(self) -> None:
        svc.invalidate_study_cache()

    def teardown_method(self) -> None:
        svc.invalidate_study_cache()

    def test_caches_load_study_per_name(self, mocker):
        loader = mocker.patch.object(
            svc, '_load_study_from_storage', side_effect=[object(), object()],
        )

        first = svc.load_study('a')
        second = svc.load_study('a')
        third = svc.load_study('b')

        assert first is second
        assert first is not third
        assert loader.call_count == 2
        loader.assert_any_call('a')
        loader.assert_any_call('b')

    def test_invalidate_single_study_evicts_only_that_entry(self, mocker):
        loader = mocker.patch.object(
            svc, '_load_study_from_storage',
            side_effect=[object(), object(), object()],
        )

        a1 = svc.load_study('a')
        b1 = svc.load_study('b')

        svc.invalidate_study_cache('a')

        a2 = svc.load_study('a')
        b2 = svc.load_study('b')

        assert a1 is not a2  # 'a' was evicted and reloaded
        assert b1 is b2      # 'b' was untouched
        assert loader.call_count == 3

    def test_invalidate_without_arg_clears_all(self, mocker):
        loader = mocker.patch.object(
            svc, '_load_study_from_storage',
            side_effect=[object(), object(), object(), object()],
        )

        svc.load_study('a')
        svc.load_study('b')
        svc.invalidate_study_cache()
        svc.load_study('a')
        svc.load_study('b')

        assert loader.call_count == 4

    def test_invalidate_missing_entry_is_noop(self):
        svc.invalidate_study_cache('does-not-exist')
