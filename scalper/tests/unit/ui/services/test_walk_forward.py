import asyncio
from unittest.mock import MagicMock

import optuna
import pytest

from data_system.models.oos_window_aggregate_model import OosWindowAggregate
from ui.models.walk_forward import (
    StudyDirection,
    StudySummary,
    TrialVerdict,
    TrialWithOos,
)
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


def _make_optuna_summary(
    name: str,
    direction: optuna.study.StudyDirection,
    n_trials: int,
    best_value: float | None,
) -> MagicMock:
    summary = MagicMock(spec=optuna.study.StudySummary)
    summary.study_name = name
    summary.direction = direction
    summary.n_trials = n_trials
    if best_value is None:
        summary.best_trial = None
    else:
        best_trial = MagicMock()
        best_trial.value = best_value
        summary.best_trial = best_trial
    return summary


@pytest.mark.ui
@pytest.mark.ui_services
@pytest.mark.walk_forward
class TestListStudiesWithSummary:
    def test_parses_pair_and_strategy_from_study_name(self, mocker):
        mocker.patch.object(svc.optuna.storages, 'RDBStorage')
        mocker.patch.object(svc.optuna, 'get_all_study_summaries', return_value=[
            _make_optuna_summary(
                'PrecisionTrendStrategy_XXBTZGBP_20240101-20240601',
                optuna.study.StudyDirection.MAXIMIZE,
                n_trials=42,
                best_value=1.7,
            ),
        ])

        result = svc.list_studies_with_summary()

        assert result == [StudySummary(
            name='PrecisionTrendStrategy_XXBTZGBP_20240101-20240601',
            pair='XXBTZGBP',
            strategy='PrecisionTrendStrategy',
            trial_count=42,
            best_is=1.7,
            direction=StudyDirection.MAXIMIZE,
        )]

    def test_handles_missing_best_trial(self, mocker):
        mocker.patch.object(svc.optuna.storages, 'RDBStorage')
        mocker.patch.object(svc.optuna, 'get_all_study_summaries', return_value=[
            _make_optuna_summary(
                'SmaStrategy_BTCGBP_20240101-20240601',
                optuna.study.StudyDirection.MAXIMIZE,
                n_trials=0,
                best_value=None,
            ),
        ])

        result = svc.list_studies_with_summary()

        assert result[0].best_is is None
        assert result[0].trial_count == 0

    def test_translates_minimise_direction(self, mocker):
        mocker.patch.object(svc.optuna.storages, 'RDBStorage')
        mocker.patch.object(svc.optuna, 'get_all_study_summaries', return_value=[
            _make_optuna_summary(
                'SmaStrategy_BTCGBP_20240101-20240601',
                optuna.study.StudyDirection.MINIMIZE,
                n_trials=10,
                best_value=0.2,
            ),
        ])

        result = svc.list_studies_with_summary()

        assert result[0].direction == StudyDirection.MINIMIZE

    def test_returns_empty_pair_and_strategy_for_non_conforming_name(self, mocker):
        mocker.patch.object(svc.optuna.storages, 'RDBStorage')
        mocker.patch.object(svc.optuna, 'get_all_study_summaries', return_value=[
            _make_optuna_summary(
                'legacy-study-name',
                optuna.study.StudyDirection.MAXIMIZE,
                n_trials=5,
                best_value=1.0,
            ),
        ])

        result = svc.list_studies_with_summary()

        assert result[0].pair == ''
        assert result[0].strategy == ''
        assert result[0].name == 'legacy-study-name'


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
    def test_left_merges_oos_scores_and_computes_verdicts(self, mocker):
        study = object()
        mocker.patch.object(svc, 'load_study', return_value=study)
        mocker.patch.object(svc, 'get_top_param_sets', return_value=[
            {'trial_number': 1, 'value': 1.5, 'params': {'a': 1}},
            {'trial_number': 2, 'value': 1.2, 'params': {'a': 2}},
            {'trial_number': 3, 'value': 0.8, 'params': {'a': 3}},
        ])
        repo = MagicMock()
        repo.get.return_value = [
            _make_oos_eval(trial_number=1, geo_mean_return=0.9),
            _make_oos_eval(trial_number=2, geo_mean_return=0.3),
            # trial 3 has no OOS row → pending
        ]

        result = svc.get_top_trials_with_oos(
            'study-x', (10.0, 20.0), n_trials=3, oos_repo=repo,
        )

        assert result == [
            TrialWithOos(
                trial_number=1, is_value=1.5, oos_score=0.9,
                delta=pytest.approx(-0.6), verdict=TrialVerdict.GENERALISES,
                params={'a': 1},
            ),
            TrialWithOos(
                trial_number=2, is_value=1.2, oos_score=0.3,
                delta=pytest.approx(-0.9), verdict=TrialVerdict.OVERFIT,
                params={'a': 2},
            ),
            TrialWithOos(
                trial_number=3, is_value=0.8, oos_score=None, delta=None,
                verdict=TrialVerdict.PENDING, params={'a': 3},
            ),
        ]
        repo.get.assert_called_once_with('study-x', 10.0, 20.0)

    def test_oos_exactly_at_threshold_generalises(self, mocker):
        mocker.patch.object(svc, 'load_study')
        mocker.patch.object(svc, 'get_top_param_sets', return_value=[
            {'trial_number': 1, 'value': 1.0, 'params': {}},
        ])
        repo = MagicMock()
        repo.get.return_value = [
            _make_oos_eval(trial_number=1, geo_mean_return=svc.OOS_OVERFIT_THRESHOLD),
        ]

        result = svc.get_top_trials_with_oos(
            's', (0.0, 1.0), n_trials=1, oos_repo=repo,
        )

        assert result[0].verdict == TrialVerdict.GENERALISES

    def test_window_none_marks_all_pending_and_skips_repo(self, mocker):
        mocker.patch.object(svc, 'load_study')
        mocker.patch.object(svc, 'get_top_param_sets', return_value=[
            {'trial_number': 1, 'value': 1.5, 'params': {}},
            {'trial_number': 2, 'value': 0.9, 'params': {}},
        ])
        repo = MagicMock()

        result = svc.get_top_trials_with_oos(
            's', None, n_trials=2, oos_repo=repo,
        )

        repo.get.assert_not_called()
        assert all(t.verdict == TrialVerdict.PENDING for t in result)
        assert all(t.oos_score is None and t.delta is None for t in result)

    def test_respects_minimise_direction(self, mocker):
        '''
        Direction-awareness lives in ``get_top_param_sets``. This test pins
        that the service forwards the study unchanged so direction is honoured.
        '''
        study = MagicMock()
        load = mocker.patch.object(svc, 'load_study', return_value=study)
        get_top = mocker.patch.object(svc, 'get_top_param_sets', return_value=[])
        repo = MagicMock(get=MagicMock(return_value=[]))

        svc.get_top_trials_with_oos('s', (0.0, 1.0), n_trials=5, oos_repo=repo)

        load.assert_called_once_with('s')
        get_top.assert_called_once_with(study, 5)


def _make_oos_eval(trial_number: int, geo_mean_return: float):
    eval_obj = MagicMock()
    eval_obj.trial_number = trial_number
    eval_obj.geo_mean_return = geo_mean_return
    return eval_obj


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
