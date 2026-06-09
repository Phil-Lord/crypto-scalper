import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

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
    def test_delegates_to_backtesting_engine_helper_by_study_name(self, mocker):
        # Given
        param_sets_sentinel = [{'trial_number': 1, 'value': 5.0, 'params': {}}]
        get_top = mocker.patch.object(
            svc, 'get_top_param_sets', return_value=param_sets_sentinel,
        )

        # When
        result = asyncio.run(svc.get_top_trials('my_study', 2))

        # Then
        get_top.assert_called_once_with('my_study', 2)
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
            'BTCGBP', 'SmaStrategy', 1700000000.0, 1701000000.0,
            n_trials=10, n_workers=4, job_repo=mock_repo,
        ))

        assert len(jobs) == 4
        assert all(j.job_type == JobType.OPTIMISE_IN_SAMPLE for j in jobs)
        # 10 trials across 4 workers = [3, 3, 2, 2]
        trial_counts = []
        for _, cmd, _ in captured:
            payload = json.loads(cmd[-1])
            trial_counts.append(payload['n_trials'])
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
                'BTCGBP', 'SmaStrategy', 1700000000.0, 1701000000.0,
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
            'BTCGBP', 'SmaStrategy', 1700000000.0, 1701000000.0,
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

        result = asyncio.run(svc.list_studies())

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

        result = asyncio.run(svc.list_oos_windows('study-x', repo))

        assert result == aggregates
        repo.aggregate_windows.assert_called_once_with(
            'study-x', svc.OOS_FLOOR, svc.OOS_DRAWDOWN_LIMIT
        )

    def test_returns_empty_when_repo_returns_no_rows(self):
        repo = MagicMock()
        repo.aggregate_windows.return_value = []

        assert asyncio.run(svc.list_oos_windows('empty', repo)) == []


@pytest.mark.ui
@pytest.mark.ui_services
@pytest.mark.walk_forward
class TestGetTopTrialsWithOos:
    def test_delegates_to_engine_by_study_name(self, mocker):
        ''' Thin offload wrapper — forwards the study name straight through. '''
        result_sentinel = [object()]
        engine_fn = mocker.patch.object(
            svc, '_get_top_trials_with_oos_from_engine', return_value=result_sentinel,
        )
        repo = MagicMock()

        result = asyncio.run(
            svc.get_top_trials_with_oos('study-x', (10.0, 20.0), n_trials=5, oos_repo=repo)
        )

        engine_fn.assert_called_once_with('study-x', (10.0, 20.0), 5, repo)
        assert result is result_sentinel


@pytest.mark.ui
@pytest.mark.ui_services
@pytest.mark.walk_forward
class TestIoBoundOffloading:
    '''
    The read helpers offload their blocking bodies to NiceGUI's thread pool
    via :func:`nicegui.run.io_bound`, so a large study never blocks the UI
    event loop. The public coroutines are thin wrappers around the private
    synchronous ``_*`` implementations.
    '''

    def test_wrapper_awaits_io_bound_with_sync_impl(self, mocker):
        sentinel = [object()]
        io_bound = mocker.patch.object(
            svc.run, 'io_bound', new=AsyncMock(return_value=sentinel),
        )
        repo = MagicMock()

        result = asyncio.run(
            svc.get_top_trials_with_oos('study-x', (1.0, 2.0), 5, repo)
        )

        io_bound.assert_awaited_once_with(
            svc._get_top_trials_with_oos, 'study-x', (1.0, 2.0), 5, repo,
        )
        assert result is sentinel

    def test_wrapper_coerces_cancelled_none_to_empty_list(self, mocker):
        '''
        ``io_bound`` returns ``None`` if the awaiting task is cancelled (client
        disconnect) or the app is stopping. The list wrappers coerce that to an
        empty list so callers never iterate over ``None``.
        '''
        mocker.patch.object(svc.run, 'io_bound', new=AsyncMock(return_value=None))

        assert asyncio.run(svc.list_studies()) == []
        assert asyncio.run(
            svc.get_top_trials_with_oos('s', None, 5, MagicMock())
        ) == []
