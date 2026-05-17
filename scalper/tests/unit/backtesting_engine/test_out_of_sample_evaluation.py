import sys
from unittest.mock import MagicMock

import optuna
import pandas as pd
import pytest

from backtesting_engine.out_of_sample_evaluation import (
    INITIAL_BALANCE,
    OOS_DRAWDOWN_LIMIT,
    OOS_FLOOR,
    TrialVerdict,
    TrialWithOos,
    _evaluate_chunk_worker,
    build_out_of_sample_command,
    chunk_param_sets,
    classify_verdict,
    evaluate_out_of_sample,
    get_top_param_sets,
    get_top_trials_with_oos,
    run_evaluation,
    run_evaluation_parallel,
    save_results,
)
from data_system.models.out_of_sample_evaluation_model import OutOfSampleEvaluation


@pytest.mark.backtesting_engine
@pytest.mark.out_of_sample_evaluation
class TestBuildOutOfSampleCommand:
    def test_includes_all_required_flags(self):
        cmd = build_out_of_sample_command(
            'PrecisionTrendStrategy_XXBTZGBP_20250101-20250401',
            num_sets=10,
            start='2025-4-1-0-0-0',
            end='2025-7-1-0-0-0',
            n_workers=2,
        )

        assert cmd[0] == sys.executable
        assert cmd[1:3] == ['-m', 'scripts.evaluate_out_of_sample']
        assert cmd[cmd.index('-sn') + 1] == 'PrecisionTrendStrategy_XXBTZGBP_20250101-20250401'
        assert cmd[cmd.index('-n') + 1] == '10'
        assert cmd[cmd.index('-s') + 1] == '2025-4-1-0-0-0'
        assert cmd[cmd.index('-e') + 1] == '2025-7-1-0-0-0'
        assert cmd[cmd.index('-w') + 1] == '2'

    def test_defaults_workers_to_one(self):
        cmd = build_out_of_sample_command('s', 1, 's', 'e')
        assert cmd[cmd.index('-w') + 1] == '1'


def _make_trial(mocker, number: int, value: float, params: dict = None, complete: bool = True):
    trial = mocker.Mock()
    trial.number = number
    trial.value = value
    trial.params = params or {}
    trial.state = optuna.trial.TrialState.COMPLETE if complete else optuna.trial.TrialState.FAIL
    return trial


def _make_study(mocker, trials: list, direction: optuna.study.StudyDirection = optuna.study.StudyDirection.MAXIMIZE):
    study = mocker.Mock()
    study.trials = trials
    study.direction = direction
    return study


@pytest.mark.backtesting_engine
@pytest.mark.out_of_sample_evaluation
class TestGetTopParamSets:
    def test_returns_top_n_trials_for_maximise_direction(self, mocker):
        # Given
        trials = [
            _make_trial(mocker, 0, 1.0, {'sma_period': 5}),
            _make_trial(mocker, 1, 3.0, {'sma_period': 10}),
            _make_trial(mocker, 2, 2.0, {'sma_period': 20}),
        ]
        study = _make_study(mocker, trials)

        # When
        result = get_top_param_sets(study, n=2, evaluated_trials=set())

        # Then
        assert len(result) == 2
        assert result[0]['value'] == 3.0
        assert result[1]['value'] == 2.0

    def test_returns_top_n_trials_for_minimise_direction(self, mocker):
        # Given
        trials = [
            _make_trial(mocker, 0, 1.0, {'sma_period': 5}),
            _make_trial(mocker, 1, 3.0, {'sma_period': 10}),
            _make_trial(mocker, 2, 2.0, {'sma_period': 20}),
        ]
        study = _make_study(mocker, trials, optuna.study.StudyDirection.MINIMIZE)

        # When
        result = get_top_param_sets(study, n=2, evaluated_trials=set())

        # Then
        assert len(result) == 2
        assert result[0]['value'] == 1.0
        assert result[1]['value'] == 2.0

    def test_excludes_already_evaluated_trials(self, mocker):
        # Given
        trials = [
            _make_trial(mocker, 0, 3.0, {'sma_period': 5}),
            _make_trial(mocker, 1, 2.0, {'sma_period': 10}),
            _make_trial(mocker, 2, 1.0, {'sma_period': 20}),
        ]
        study = _make_study(mocker, trials)

        # When
        result = get_top_param_sets(study, n=3, evaluated_trials={0})

        # Then
        assert len(result) == 2
        assert all(r['trial_number'] != 0 for r in result)

    def test_returns_empty_list_when_all_evaluated(self, mocker):
        # Given
        trials = [
            _make_trial(mocker, 0, 3.0),
            _make_trial(mocker, 1, 2.0),
        ]
        study = _make_study(mocker, trials)

        # When
        result = get_top_param_sets(study, n=2, evaluated_trials={0, 1})

        # Then
        assert result == []

    def test_excludes_incomplete_trials(self, mocker):
        # Given
        trials = [
            _make_trial(mocker, 0, 3.0, complete=True),
            _make_trial(mocker, 1, 5.0, complete=False),
        ]
        study = _make_study(mocker, trials)

        # When
        result = get_top_param_sets(study, n=2, evaluated_trials=set())

        # Then
        assert len(result) == 1
        assert result[0]['trial_number'] == 0

    def test_returns_correct_dict_structure(self, mocker):
        # Given
        params = {'sma_period': 10, 'ema_period': 20}
        trial = _make_trial(mocker, 42, 1.5, params)
        study = _make_study(mocker, [trial])

        # When
        result = get_top_param_sets(study, n=1, evaluated_trials=set())

        # Then
        assert result == [{'trial_number': 42, 'value': 1.5, 'params': params}]

    def test_returns_fewer_than_n_when_not_enough_trials(self, mocker):
        # Given
        trials = [_make_trial(mocker, 0, 1.0)]
        study = _make_study(mocker, trials)

        # When
        result = get_top_param_sets(study, n=5, evaluated_trials=set())

        # Then
        assert len(result) == 1

    def test_default_evaluated_trials_includes_every_completed_trial(self, mocker):
        # Given — the UI preview path passes no evaluated_trials and expects to
        # see every completed trial regardless of prior evaluation state.
        trials = [
            _make_trial(mocker, 0, 3.0, {'sma_period': 5}),
            _make_trial(mocker, 1, 2.0, {'sma_period': 10}),
        ]
        study = _make_study(mocker, trials)

        # When
        result = get_top_param_sets(study, n=2)

        # Then
        assert {r['trial_number'] for r in result} == {0, 1}


@pytest.mark.backtesting_engine
@pytest.mark.out_of_sample_evaluation
class TestRunEvaluation:
    @pytest.fixture
    def mock_engine(self, mocker):
        engine = mocker.Mock()
        engine.strategy = mocker.Mock()
        engine.strategy.__class__.__name__ = 'TestStrategy'
        engine.get_final_quote_balance.return_value = 1100.0
        return engine

    @pytest.fixture
    def sample_param_sets(self):
        return [{'trial_number': 0, 'value': 1.5, 'params': {'sma_period': 10}}]

    @pytest.fixture
    def sample_windows(self):
        return [(pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01'))]

    def test_returns_result_for_each_param_set(self, mocker, mock_engine, sample_windows):
        # Given
        mocker.patch('backtesting_engine.window_evaluation.create_strategy')
        param_sets = [
            {'trial_number': 0, 'value': 1.5, 'params': {'sma_period': 10}},
            {'trial_number': 1, 'value': 1.3, 'params': {'sma_period': 20}},
        ]

        # When
        results = run_evaluation(mock_engine, param_sets, sample_windows)

        # Then
        assert len(results) == 2

    def test_result_has_correct_structure(self, mocker, mock_engine, sample_param_sets, sample_windows):
        # Given
        mocker.patch('backtesting_engine.window_evaluation.create_strategy')

        # When
        results = run_evaluation(mock_engine, sample_param_sets, sample_windows)

        # Then
        assert len(results) == 1
        assert set(results[0].keys()) == {'trial_number', 'is_value', 'oos_balance_ratio'}
        assert results[0]['trial_number'] == 0
        assert results[0]['is_value'] == 1.5

    def test_calculates_geometric_mean_correctly(self, mocker, mock_engine, sample_param_sets):
        # Given
        mocker.patch('backtesting_engine.window_evaluation.create_strategy')
        mock_engine.get_final_quote_balance.side_effect = [1200.0, 1050.0]
        windows = [
            (pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01')),
            (pd.Timestamp('2021-02-01'), pd.Timestamp('2021-05-01')),
        ]

        # When
        results = run_evaluation(mock_engine, sample_param_sets, windows)

        # Then
        expected_geo_mean = (1200.0 * 1050.0) ** 0.5
        expected_ratio = expected_geo_mean / INITIAL_BALANCE
        assert results[0]['oos_balance_ratio'] == pytest.approx(expected_ratio)

    def test_resets_strategy_between_windows(self, mocker, mock_engine, sample_param_sets):
        # Given
        mock_strategy = mocker.Mock()
        mocker.patch(
            'backtesting_engine.window_evaluation.create_strategy',
            return_value=mock_strategy,
        )
        windows = [
            (pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01')),
            (pd.Timestamp('2021-02-01'), pd.Timestamp('2021-05-01')),
        ]

        # When
        run_evaluation(mock_engine, sample_param_sets, windows)

        # Then
        assert mock_strategy.reset.call_count == len(windows)

    def test_sets_ohlc_window_once_per_window(self, mocker, mock_engine, sample_param_sets):
        # Given
        mocker.patch('backtesting_engine.window_evaluation.create_strategy')
        windows = [
            (pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01')),
            (pd.Timestamp('2021-02-01'), pd.Timestamp('2021-05-01')),
        ]

        # When
        run_evaluation(mock_engine, sample_param_sets, windows)

        # Then
        assert mock_engine.set_ohlc_window.call_count == len(windows)
        for window_start, window_end in windows:
            mock_engine.set_ohlc_window.assert_any_call(window_start, window_end)

    def test_creates_new_strategy_for_each_param_set(self, mocker, mock_engine, sample_windows):
        # Given
        mock_create_strategy = mocker.patch(
            'backtesting_engine.window_evaluation.create_strategy',
        )
        param_sets = [
            {'trial_number': 0, 'value': 1.5, 'params': {'sma_period': 10}},
            {'trial_number': 1, 'value': 1.3, 'params': {'sma_period': 20}},
        ]

        # When
        run_evaluation(mock_engine, param_sets, sample_windows)

        # Then
        assert mock_create_strategy.call_count == len(param_sets)


@pytest.mark.backtesting_engine
@pytest.mark.out_of_sample_evaluation
class TestSaveResults:

    def test_calls_repository_add_once(self, mocker):
        # Given
        repository = mocker.Mock()
        results = [{'trial_number': 0, 'is_value': 1.5, 'oos_balance_ratio': 1.05}]

        # When
        save_results(repository, results, 'TestStudy', 1609459200.0, 1617235200.0)

        # Then
        assert repository.add.call_count == 1

    def test_creates_evaluation_for_each_result(self, mocker):
        # Given
        repository = mocker.Mock()
        results = [
            {'trial_number': 0, 'is_value': 1.5, 'oos_balance_ratio': 1.05},
            {'trial_number': 1, 'is_value': 1.2, 'oos_balance_ratio': 0.97},
        ]

        # When
        save_results(repository, results, 'TestStudy', 1609459200.0, 1617235200.0)

        # Then
        evaluations = repository.add.call_args[0][0]
        assert len(evaluations) == 2

    def test_evaluation_fields_are_correct(self, mocker):
        # Given
        repository = mocker.Mock()
        results = [{'trial_number': 7, 'is_value': 1.4, 'oos_balance_ratio': 1.1}]
        study_name = 'TestStudy_XXBTZGBP_20210101-20210401'
        start = 1609459200.0
        end = 1617235200.0

        # When
        save_results(repository, results, study_name, start, end)

        # Then
        evaluations = repository.add.call_args[0][0]
        ev = evaluations[0]
        assert isinstance(ev, OutOfSampleEvaluation)
        assert ev.study_name == study_name
        assert ev.trial_number == 7
        assert ev.start_timestamp == start
        assert ev.end_timestamp == end
        assert ev.is_value == pytest.approx(1.4)
        assert ev.oos_balance_ratio == pytest.approx(1.1)

    def test_all_evaluations_share_study_name_and_period(self, mocker):
        # Given
        repository = mocker.Mock()
        results = [
            {'trial_number': 0, 'is_value': 1.5, 'oos_balance_ratio': 1.05},
            {'trial_number': 1, 'is_value': 1.2, 'oos_balance_ratio': 0.97},
        ]
        study_name = 'SharedStudy'
        start = 1609459200.0
        end = 1617235200.0

        # When
        save_results(repository, results, study_name, start, end)

        # Then
        evaluations = repository.add.call_args[0][0]
        for ev in evaluations:
            assert ev.study_name == study_name
            assert ev.start_timestamp == start
            assert ev.end_timestamp == end


@pytest.mark.backtesting_engine
@pytest.mark.out_of_sample_evaluation
class TestChunkParamSets:
    def test_splits_evenly_when_divisible(self):
        param_sets = [{'trial_number': i} for i in range(6)]

        chunks = chunk_param_sets(param_sets, n_chunks=3)

        assert [len(c) for c in chunks] == [2, 2, 2]

    def test_distributes_remainder_to_earlier_chunks(self):
        param_sets = [{'trial_number': i} for i in range(7)]

        chunks = chunk_param_sets(param_sets, n_chunks=3)

        assert [len(c) for c in chunks] == [3, 2, 2]

    def test_caps_chunk_count_at_param_set_count(self):
        param_sets = [{'trial_number': 0}, {'trial_number': 1}]

        chunks = chunk_param_sets(param_sets, n_chunks=10)

        assert len(chunks) == 2
        assert all(len(c) == 1 for c in chunks)

    def test_preserves_order_across_chunks(self):
        param_sets = [{'trial_number': i} for i in range(5)]

        chunks = chunk_param_sets(param_sets, n_chunks=2)

        flattened = [ps['trial_number'] for chunk in chunks for ps in chunk]
        assert flattened == [0, 1, 2, 3, 4]

    def test_treats_zero_or_negative_as_single_chunk(self):
        param_sets = [{'trial_number': 0}, {'trial_number': 1}]

        chunks = chunk_param_sets(param_sets, n_chunks=0)

        assert len(chunks) == 1
        assert chunks[0] == param_sets


@pytest.mark.backtesting_engine
@pytest.mark.out_of_sample_evaluation
class TestRunEvaluationParallel:
    @pytest.fixture
    def windows(self):
        return [(pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01'))]

    @pytest.fixture
    def param_sets(self):
        return [
            {'trial_number': 0, 'value': 1.5, 'params': {'sma_period': 10}},
            {'trial_number': 1, 'value': 1.3, 'params': {'sma_period': 20}},
            {'trial_number': 2, 'value': 1.1, 'params': {'sma_period': 30}},
        ]

    @pytest.fixture(autouse=True)
    def passthrough_as_completed(self, mocker):
        # The real as_completed expects concurrent.futures.Future internals; with
        # mocked futures we substitute a passthrough that yields them in submission
        # order so the test can drive future.result() deterministically.
        mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.as_completed',
            side_effect=lambda fs: iter(list(fs)),
        )

    def test_dispatches_one_task_per_chunk(self, mocker, param_sets, windows):
        # Given
        executor = mocker.MagicMock()
        executor.__enter__.return_value = executor
        future = mocker.Mock()
        future.result.return_value = []
        executor.submit.return_value = future
        mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.ProcessPoolExecutor',
            return_value=executor,
        )

        # When
        run_evaluation_parallel(
            'XXBTZGBP', 'PrecisionTrendStrategy', param_sets, windows,
            start=1609459200.0, end=1617235200.0, n_workers=3,
        )

        # Then
        assert executor.submit.call_count == 3

    def test_aggregates_worker_results(self, mocker, param_sets, windows):
        # Given
        executor = mocker.MagicMock()
        executor.__enter__.return_value = executor
        worker_outputs = [
            [{'trial_number': 0, 'oos_balance_ratio': 1.05}],
            [{'trial_number': 1, 'oos_balance_ratio': 0.97}],
            [{'trial_number': 2, 'oos_balance_ratio': 1.10}],
        ]
        futures = []
        for output in worker_outputs:
            f = mocker.Mock()
            f.result.return_value = output
            futures.append(f)
        executor.submit.side_effect = futures
        mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.ProcessPoolExecutor',
            return_value=executor,
        )

        # When
        results = run_evaluation_parallel(
            'XXBTZGBP', 'PrecisionTrendStrategy', param_sets, windows,
            start=1609459200.0, end=1617235200.0, n_workers=3,
        )

        # Then
        # Order is not guaranteed (workers complete in arbitrary order under
        # as_completed), so compare as a set.
        assert {r['trial_number'] for r in results} == {0, 1, 2}

    def test_caps_executor_workers_at_chunk_count(self, mocker, param_sets, windows):
        # Given
        process_pool = mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.ProcessPoolExecutor',
        )
        executor = process_pool.return_value
        executor.__enter__.return_value = executor
        future = mocker.Mock()
        future.result.return_value = []
        executor.submit.return_value = future

        # When
        # 3 param sets, 10 workers requested → only 3 chunks possible.
        run_evaluation_parallel(
            'XXBTZGBP', 'PrecisionTrendStrategy', param_sets, windows,
            start=1609459200.0, end=1617235200.0, n_workers=10,
        )

        # Then
        process_pool.assert_called_once_with(max_workers=3)


@pytest.mark.backtesting_engine
@pytest.mark.out_of_sample_evaluation
class TestEvaluateOutOfSample:
    @pytest.fixture
    def patches(self, mocker):
        mocker.patch('backtesting_engine.out_of_sample_evaluation.load_study')

        eval_repo = mocker.Mock()
        eval_repo.get_evaluated_trial_numbers.return_value = set()
        mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.SQLAlchemyOutOfSampleEvaluationRepository',
            return_value=eval_repo,
        )
        mocker.patch('backtesting_engine.out_of_sample_evaluation.SQLAlchemyClient')

        top_param_sets = [
            {'trial_number': 0, 'value': 1.5, 'params': {'sma_period': 10}},
            {'trial_number': 1, 'value': 1.3, 'params': {'sma_period': 20}},
        ]
        mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.get_top_param_sets',
            return_value=top_param_sets,
        )
        mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.create_windows',
            return_value=[(pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01'))],
        )

        run_serial = mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.run_evaluation',
            return_value=[],
        )
        run_parallel = mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.run_evaluation_parallel',
            return_value=[],
        )
        build_engine = mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.build_engine',
        )
        mocker.patch('backtesting_engine.out_of_sample_evaluation.save_results')

        return {
            'run_serial': run_serial,
            'run_parallel': run_parallel,
            'build_engine': build_engine,
            'top_param_sets': top_param_sets,
        }

    def test_uses_serial_path_by_default(self, patches):
        # When
        evaluate_out_of_sample(
            'PrecisionTrendStrategy_XXBTZGBP_20250101-20250401', num_sets=2, start=1.0, end=2.0)

        # Then
        patches['run_serial'].assert_called_once()
        patches['run_parallel'].assert_not_called()

    def test_uses_serial_path_when_n_workers_is_one(self, patches):
        # When
        evaluate_out_of_sample('PrecisionTrendStrategy_XXBTZGBP_20250101-20250401',
                               num_sets=2, start=1.0, end=2.0, n_workers=1)

        # Then
        patches['run_serial'].assert_called_once()
        patches['run_parallel'].assert_not_called()

    def test_uses_parallel_path_when_n_workers_above_one(self, patches):
        # When
        evaluate_out_of_sample('PrecisionTrendStrategy_XXBTZGBP_20250101-20250401',
                               num_sets=2, start=1.0, end=2.0, n_workers=4)

        # Then
        patches['run_parallel'].assert_called_once()
        patches['run_serial'].assert_not_called()
        # Engine is built per-worker by run_evaluation_parallel, not in the main process.
        patches['build_engine'].assert_not_called()

    def test_passes_n_workers_through_to_parallel_runner(self, patches):
        # When
        evaluate_out_of_sample('PrecisionTrendStrategy_XXBTZGBP_20250101-20250401',
                               num_sets=2, start=1.0, end=2.0, n_workers=4)

        # Then
        call = patches['run_parallel'].call_args
        assert 4 in call.args or call.kwargs.get('n_workers') == 4

    def test_no_evaluation_when_no_param_sets(self, mocker, patches):
        # Given
        mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.get_top_param_sets',
            return_value=[],
        )

        # When
        evaluate_out_of_sample('PrecisionTrendStrategy_XXBTZGBP_20250101-20250401',
                               num_sets=2, start=1.0, end=2.0, n_workers=4)

        # Then
        patches['run_serial'].assert_not_called()
        patches['run_parallel'].assert_not_called()

    def test_forwards_progress_callback_to_serial_runner(self, mocker, patches):
        # Given
        cb = mocker.Mock()

        # When
        evaluate_out_of_sample(
            'PrecisionTrendStrategy_XXBTZGBP_20250101-20250401', num_sets=2, start=1.0, end=2.0, progress_callback=cb,
        )

        # Then
        passed = patches['run_serial'].call_args.args[3] \
            if len(patches['run_serial'].call_args.args) > 3 \
            else patches['run_serial'].call_args.kwargs.get('progress_callback')
        assert passed is cb

    def test_forwards_progress_callback_to_parallel_runner(self, mocker, patches):
        # Given
        cb = mocker.Mock()

        # When
        evaluate_out_of_sample(
            'PrecisionTrendStrategy_XXBTZGBP_20250101-20250401', num_sets=2, start=1.0, end=2.0, n_workers=4, progress_callback=cb,
        )

        # Then
        call = patches['run_parallel'].call_args
        passed = call.args[7] if len(call.args) > 7 else call.kwargs.get('progress_callback')
        assert passed is cb

    def test_serial_builds_engine_with_strategy_and_pair_parsed_from_study_name(self, patches):
        # When
        evaluate_out_of_sample(
            'SmaStrategy_XXBTZGBP_20250101-20250401', num_sets=2, start=1.0, end=2.0,
        )

        # Then — the first two positional args are the pair and strategy_name, derived
        # from the study name rather than a hardcoded module constant.
        call = patches['build_engine'].call_args
        assert call.args[0] == 'XXBTZGBP'
        assert call.args[1] == 'SmaStrategy'

    def test_parallel_passes_strategy_and_pair_parsed_from_study_name(self, patches):
        # When
        evaluate_out_of_sample(
            'SmaStrategy_XXBTZGBP_20250101-20250401',
            num_sets=2, start=1.0, end=2.0, n_workers=4,
        )

        # Then
        call = patches['run_parallel'].call_args
        assert call.args[0] == 'XXBTZGBP'
        assert call.args[1] == 'SmaStrategy'


@pytest.mark.backtesting_engine
@pytest.mark.out_of_sample_evaluation
class TestProgressCallbackInvocation:
    @pytest.fixture
    def windows(self):
        return [(pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01'))]

    def test_serial_calls_user_callback_once_per_param_set(self, mocker, windows):
        # Given
        mocker.patch('backtesting_engine.window_evaluation.create_strategy')
        engine = mocker.Mock()
        engine.get_final_quote_balance.return_value = 1100.0
        param_sets = [
            {'trial_number': 0, 'value': 1.5, 'params': {}},
            {'trial_number': 1, 'value': 1.3, 'params': {}},
            {'trial_number': 2, 'value': 1.1, 'params': {}},
        ]
        cb = mocker.Mock()

        # When
        run_evaluation(engine, param_sets, windows, progress_callback=cb)

        # Then
        assert cb.call_count == 3

    def test_serial_runs_without_callback_when_none_provided(self, mocker, windows):
        # Given
        mocker.patch('backtesting_engine.window_evaluation.create_strategy')
        engine = mocker.Mock()
        engine.get_final_quote_balance.return_value = 1100.0
        param_sets = [{'trial_number': 0, 'value': 1.5, 'params': {}}]

        # When / Then — should complete without raising even without a callback.
        results = run_evaluation(engine, param_sets, windows)
        assert len(results) == 1

    def test_parallel_calls_user_callback_once_per_param_set(self, mocker, windows):
        # Given
        executor = mocker.MagicMock()
        executor.__enter__.return_value = executor
        worker_outputs = [
            [{'trial_number': 0, 'oos_balance_ratio': 1.05},
             {'trial_number': 1, 'oos_balance_ratio': 0.95}],
            [{'trial_number': 2, 'oos_balance_ratio': 1.10}],
        ]
        futures = []
        for output in worker_outputs:
            f = mocker.Mock()
            f.result.return_value = output
            futures.append(f)
        executor.submit.side_effect = futures
        mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.ProcessPoolExecutor',
            return_value=executor,
        )
        mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.as_completed',
            side_effect=lambda fs: iter(list(fs)),
        )
        cb = mocker.Mock()
        param_sets = [{'trial_number': i, 'value': 1.0, 'params': {}} for i in range(3)]

        # When
        run_evaluation_parallel(
            'XXBTZGBP', 'PrecisionTrendStrategy', param_sets, windows,
            start=1.0, end=2.0, n_workers=2, progress_callback=cb,
        )

        # Then
        assert cb.call_count == 3


@pytest.mark.backtesting_engine
@pytest.mark.out_of_sample_evaluation
class TestSerialParallelParity:
    def test_worker_produces_same_geo_mean_as_serial(self, mocker):
        # Given — fixed balances so both paths see deterministic, identical input.
        # Four calls total: serial processes two param_sets, then the worker processes
        # the same two param_sets again.
        mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.evaluate_param_set_over_windows',
            side_effect=[[1200.0], [800.0], [1200.0], [800.0]],
        )
        mock_engine = mocker.Mock()
        mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.build_engine',
            return_value=mock_engine,
        )

        param_sets = [
            {'trial_number': 0, 'value': 1.5, 'params': {'sma_period': 10}},
            {'trial_number': 1, 'value': 1.3, 'params': {'sma_period': 20}},
        ]
        windows = [(pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01'))]

        # When
        serial_results = run_evaluation(mock_engine, param_sets,
                                        windows, progress_callback=lambda: None)
        worker_results = _evaluate_chunk_worker(
            'XXBTZGBP', 'PrecisionTrendStrategy', param_sets, windows,
            start=1609459200.0, end=1617235200.0,
        )

        # Then
        serial_by_trial = {r['trial_number']: r['oos_balance_ratio'] for r in serial_results}
        worker_by_trial = {r['trial_number']: r['oos_balance_ratio'] for r in worker_results}
        assert serial_by_trial == worker_by_trial


@pytest.mark.backtesting_engine
@pytest.mark.out_of_sample_evaluation
class TestTrialVerdict:
    def test_values_use_british_spelling(self):
        assert TrialVerdict.PENDING.value == 'pending'
        assert TrialVerdict.GENERALISES.value == 'generalises'
        assert TrialVerdict.OVERFIT.value == 'overfit'

    def test_is_string_compatible(self):
        assert TrialVerdict.PENDING == 'pending'
        assert TrialVerdict.GENERALISES == 'generalises'
        assert TrialVerdict.OVERFIT == 'overfit'


@pytest.mark.backtesting_engine
@pytest.mark.out_of_sample_evaluation
class TestTrialWithOos:
    @pytest.fixture
    def sample_trial_data(self):
        return {
            'trial_number': 7,
            'is_value': 1.5,
            'oos_score': 0.9,
            'delta': -0.6,
            'verdict': TrialVerdict.GENERALISES,
            'params': {'sma_period': 20},
        }

    def test_creates_trial_with_all_fields(self, sample_trial_data):
        trial = TrialWithOos(**sample_trial_data)

        assert trial.trial_number == 7
        assert trial.is_value == 1.5
        assert trial.oos_score == 0.9
        assert trial.delta == -0.6
        assert trial.verdict == TrialVerdict.GENERALISES
        assert trial.params == {'sma_period': 20}

    def test_oos_score_and_delta_can_be_none(self, sample_trial_data):
        sample_trial_data['oos_score'] = None
        sample_trial_data['delta'] = None
        sample_trial_data['verdict'] = TrialVerdict.PENDING

        trial = TrialWithOos(**sample_trial_data)

        assert trial.oos_score is None
        assert trial.delta is None
        assert trial.verdict == TrialVerdict.PENDING

    def test_trial_is_frozen(self, sample_trial_data):
        trial = TrialWithOos(**sample_trial_data)
        with pytest.raises(AttributeError):
            trial.oos_score = 0.99

    def test_supports_empty_params(self, sample_trial_data):
        sample_trial_data['params'] = {}
        trial = TrialWithOos(**sample_trial_data)
        assert trial.params == {}


def _make_oos_eval(trial_number: int, oos_balance_ratio: float):
    eval_obj = MagicMock()
    eval_obj.trial_number = trial_number
    eval_obj.oos_balance_ratio = oos_balance_ratio
    return eval_obj


@pytest.mark.backtesting_engine
@pytest.mark.out_of_sample_evaluation
class TestClassifyVerdict:
    def test_returns_pending_when_oos_is_none(self):
        assert classify_verdict(is_value=1.5, oos_score=None) == TrialVerdict.PENDING

    def test_passes_both_floor_and_drawdown(self):
        # OOS at floor + small drawdown -> generalises
        assert classify_verdict(is_value=1.2, oos_score=1.1) == TrialVerdict.GENERALISES

    def test_fails_floor_only(self):
        # Drawdown is fine (0.15 <= 0.5) but oos below the 1.0 floor.
        assert classify_verdict(is_value=1.05, oos_score=0.9) == TrialVerdict.OVERFIT

    def test_fails_drawdown_only(self):
        # OOS above floor (1.1 >= 1.0) but is - oos = 0.9 > 0.5 drawdown limit.
        assert classify_verdict(is_value=2.0, oos_score=1.1) == TrialVerdict.OVERFIT

    def test_fails_both(self):
        assert classify_verdict(is_value=1.5, oos_score=0.4) == TrialVerdict.OVERFIT

    def test_oos_exactly_at_floor_generalises(self):
        # Floor check is >=, so an exactly-at value passes.
        assert classify_verdict(is_value=OOS_FLOOR, oos_score=OOS_FLOOR) == TrialVerdict.GENERALISES

    def test_oos_just_below_floor_overfits(self):
        assert (
            classify_verdict(is_value=OOS_FLOOR, oos_score=OOS_FLOOR - 1e-9)
            == TrialVerdict.OVERFIT
        )

    def test_drawdown_exactly_at_limit_generalises(self):
        # Drawdown check is <=, so an exactly-at delta passes.
        assert (
            classify_verdict(is_value=OOS_FLOOR + OOS_DRAWDOWN_LIMIT, oos_score=OOS_FLOOR)
            == TrialVerdict.GENERALISES
        )

    def test_drawdown_just_above_limit_overfits(self):
        assert (
            classify_verdict(
                is_value=OOS_FLOOR + OOS_DRAWDOWN_LIMIT + 1e-9,
                oos_score=OOS_FLOOR,
            )
            == TrialVerdict.OVERFIT
        )


@pytest.mark.backtesting_engine
@pytest.mark.out_of_sample_evaluation
class TestGetTopTrialsWithOos:
    def test_left_merges_oos_scores_and_computes_verdicts(self, mocker):
        study = MagicMock(study_name='study-x')
        mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.get_top_param_sets',
            return_value=[
                {'trial_number': 1, 'value': 1.2, 'params': {'a': 1}},
                {'trial_number': 2, 'value': 1.5, 'params': {'a': 2}},
                {'trial_number': 3, 'value': 0.8, 'params': {'a': 3}},
            ],
        )
        repo = MagicMock()
        repo.get.return_value = [
            _make_oos_eval(trial_number=1, oos_balance_ratio=1.1),  # passes both
            _make_oos_eval(trial_number=2, oos_balance_ratio=0.3),  # fails floor
            # trial 3 has no OOS row -> pending
        ]

        result = get_top_trials_with_oos(study, (10.0, 20.0), n_trials=3, oos_repo=repo)

        assert result == [
            TrialWithOos(
                trial_number=1, is_value=1.2, oos_score=1.1,
                delta=pytest.approx(-0.1), verdict=TrialVerdict.GENERALISES,
                params={'a': 1},
            ),
            TrialWithOos(
                trial_number=2, is_value=1.5, oos_score=0.3,
                delta=pytest.approx(-1.2), verdict=TrialVerdict.OVERFIT,
                params={'a': 2},
            ),
            TrialWithOos(
                trial_number=3, is_value=0.8, oos_score=None, delta=None,
                verdict=TrialVerdict.PENDING, params={'a': 3},
            ),
        ]
        repo.get.assert_called_once_with('study-x', 10.0, 20.0)

    def test_window_none_marks_all_pending_and_skips_repo(self, mocker):
        study = MagicMock(study_name='s')
        mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.get_top_param_sets',
            return_value=[
                {'trial_number': 1, 'value': 1.5, 'params': {}},
                {'trial_number': 2, 'value': 0.9, 'params': {}},
            ],
        )
        repo = MagicMock()

        result = get_top_trials_with_oos(study, None, n_trials=2, oos_repo=repo)

        repo.get.assert_not_called()
        assert all(t.verdict == TrialVerdict.PENDING for t in result)
        assert all(t.oos_score is None and t.delta is None for t in result)

    def test_respects_minimise_direction(self, mocker):
        '''
        Direction-awareness lives in ``get_top_param_sets``. This test pins
        that the study is forwarded unchanged so direction is honoured.
        '''
        study = MagicMock(study_name='s')
        get_top = mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.get_top_param_sets',
            return_value=[],
        )
        repo = MagicMock(get=MagicMock(return_value=[]))

        get_top_trials_with_oos(study, (0.0, 1.0), n_trials=5, oos_repo=repo)

        get_top.assert_called_once_with(study, 5)

    def test_returns_empty_when_no_top_trials(self, mocker):
        study = MagicMock(study_name='s')
        mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.get_top_param_sets',
            return_value=[],
        )
        repo = MagicMock()
        repo.get.return_value = []

        result = get_top_trials_with_oos(study, (0.0, 1.0), n_trials=10, oos_repo=repo)

        assert result == []

    def test_oos_for_trial_outside_top_n_is_ignored(self, mocker):
        '''
        OOS rows for trials that aren't in the top-N selection are silently
        dropped — the function joins onto top-trials, not the other way around.
        '''
        study = MagicMock(study_name='s')
        mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.get_top_param_sets',
            return_value=[{'trial_number': 1, 'value': 1.5, 'params': {}}],
        )
        repo = MagicMock()
        repo.get.return_value = [
            _make_oos_eval(trial_number=1, oos_balance_ratio=0.9),
            _make_oos_eval(trial_number=99, oos_balance_ratio=0.95),
        ]

        result = get_top_trials_with_oos(study, (0.0, 1.0), n_trials=1, oos_repo=repo)

        assert len(result) == 1
        assert result[0].trial_number == 1
        assert result[0].oos_score == 0.9

    def test_window_with_no_oos_rows_marks_all_pending(self, mocker):
        '''
        Distinct from ``window=None``: a real window is provided (so the repo
        is queried), but the repo returns nothing — all trials should still
        come back as pending rather than overfit.
        '''
        study = MagicMock(study_name='s')
        mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.get_top_param_sets',
            return_value=[
                {'trial_number': 1, 'value': 1.5, 'params': {}},
                {'trial_number': 2, 'value': 1.2, 'params': {}},
            ],
        )
        repo = MagicMock()
        repo.get.return_value = []

        result = get_top_trials_with_oos(study, (10.0, 20.0), n_trials=2, oos_repo=repo)

        repo.get.assert_called_once_with('s', 10.0, 20.0)
        assert all(t.verdict == TrialVerdict.PENDING for t in result)
        assert all(t.oos_score is None and t.delta is None for t in result)
