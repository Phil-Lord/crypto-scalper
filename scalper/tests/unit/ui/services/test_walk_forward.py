import asyncio

import pytest

from ui.services import walk_forward as svc


@pytest.mark.ui
@pytest.mark.ui_services
@pytest.mark.walk_forward
class TestParseProgress:
    def test_parses_progress_line(self):
        event = svc.parse_progress('PROGRESS {"trial": 3, "value": 1.2, "best": 1.5}')
        assert event == {
            'event': 'PROGRESS',
            'payload': {'trial': 3, 'value': 1.2, 'best': 1.5},
        }

    def test_parses_done_line(self):
        event = svc.parse_progress('DONE {"trials": 100}')
        assert event == {'event': 'DONE', 'payload': {'trials': 100}}

    def test_returns_none_for_blank_line(self):
        assert svc.parse_progress('') is None

    def test_returns_none_for_unknown_event(self):
        assert svc.parse_progress('LOG {"foo": 1}') is None

    def test_returns_none_for_malformed_json(self):
        assert svc.parse_progress('PROGRESS not-json') is None

    def test_returns_none_when_payload_is_not_object(self):
        assert svc.parse_progress('PROGRESS [1, 2, 3]') is None

    def test_returns_none_when_no_payload(self):
        assert svc.parse_progress('PROGRESS') is None

    def test_strips_trailing_whitespace(self):
        event = svc.parse_progress('PROGRESS {"trial": 0}\n')
        assert event['payload'] == {'trial': 0}


@pytest.mark.ui
@pytest.mark.ui_services
@pytest.mark.walk_forward
class TestSplitTrials:
    def test_splits_evenly(self):
        assert svc._split_trials(10, 5) == [2, 2, 2, 2, 2]

    def test_distributes_remainder_to_first_workers(self):
        assert svc._split_trials(11, 4) == [3, 3, 3, 2]

    def test_drops_workers_when_more_workers_than_trials(self):
        assert svc._split_trials(3, 8) == [1, 1, 1]

    def test_returns_empty_when_no_trials(self):
        assert svc._split_trials(0, 4) == []

    def test_returns_empty_when_no_workers(self):
        assert svc._split_trials(10, 0) == []


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
        assert {e['event'] for _, e in captured} == {'PROGRESS', 'DONE'}
