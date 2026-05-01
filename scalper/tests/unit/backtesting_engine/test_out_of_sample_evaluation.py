import optuna
import pandas as pd
import pytest

from backtesting_engine.out_of_sample_evaluation import (
    INITIAL_BALANCE,
    chunk_param_sets,
    evaluate_out_of_sample,
    evaluate_param_set,
    get_top_param_sets,
    run_evaluation,
    run_evaluation_parallel,
    save_results,
)
from data_system.models.out_of_sample_evaluation_model import OutOfSampleEvaluation


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
        assert set(results[0].keys()) == {'trial_number', 'geo_mean_return'}
        assert results[0]['trial_number'] == 0

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
        assert results[0]['geo_mean_return'] == pytest.approx(expected_ratio)

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
        results = [{'trial_number': 0, 'geo_mean_return': 1.05}]

        # When
        save_results(repository, results, 'TestStudy', 1609459200.0, 1617235200.0)

        # Then
        assert repository.add.call_count == 1

    def test_creates_evaluation_for_each_result(self, mocker):
        # Given
        repository = mocker.Mock()
        results = [
            {'trial_number': 0, 'geo_mean_return': 1.05},
            {'trial_number': 1, 'geo_mean_return': 0.97},
        ]

        # When
        save_results(repository, results, 'TestStudy', 1609459200.0, 1617235200.0)

        # Then
        evaluations = repository.add.call_args[0][0]
        assert len(evaluations) == 2

    def test_evaluation_fields_are_correct(self, mocker):
        # Given
        repository = mocker.Mock()
        results = [{'trial_number': 7, 'geo_mean_return': 1.1}]
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
        assert ev.geo_mean_return == pytest.approx(1.1)

    def test_all_evaluations_share_study_name_and_period(self, mocker):
        # Given
        repository = mocker.Mock()
        results = [
            {'trial_number': 0, 'geo_mean_return': 1.05},
            {'trial_number': 1, 'geo_mean_return': 0.97},
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

    def test_aggregates_worker_results_in_order(self, mocker, param_sets, windows):
        # Given
        executor = mocker.MagicMock()
        executor.__enter__.return_value = executor
        worker_outputs = [
            [{'trial_number': 0, 'geo_mean_return': 1.05}],
            [{'trial_number': 1, 'geo_mean_return': 0.97}],
            [{'trial_number': 2, 'geo_mean_return': 1.10}],
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
        assert [r['trial_number'] for r in results] == [0, 1, 2]

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
        evaluate_out_of_sample('study', num_sets=2, start=1.0, end=2.0)

        # Then
        patches['run_serial'].assert_called_once()
        patches['run_parallel'].assert_not_called()

    def test_uses_serial_path_when_n_workers_is_one(self, patches):
        # When
        evaluate_out_of_sample('study', num_sets=2, start=1.0, end=2.0, n_workers=1)

        # Then
        patches['run_serial'].assert_called_once()
        patches['run_parallel'].assert_not_called()

    def test_uses_parallel_path_when_n_workers_above_one(self, patches):
        # When
        evaluate_out_of_sample('study', num_sets=2, start=1.0, end=2.0, n_workers=4)

        # Then
        patches['run_parallel'].assert_called_once()
        patches['run_serial'].assert_not_called()
        # Engine is built per-worker by run_evaluation_parallel, not in the main process.
        patches['build_engine'].assert_not_called()

    def test_passes_n_workers_through_to_parallel_runner(self, patches):
        # When
        evaluate_out_of_sample('study', num_sets=2, start=1.0, end=2.0, n_workers=4)

        # Then
        kwargs = patches['run_parallel'].call_args
        assert 4 in kwargs.args or kwargs.kwargs.get('n_workers') == 4

    def test_no_evaluation_when_no_param_sets(self, mocker, patches):
        # Given
        mocker.patch(
            'backtesting_engine.out_of_sample_evaluation.get_top_param_sets',
            return_value=[],
        )

        # When
        evaluate_out_of_sample('study', num_sets=2, start=1.0, end=2.0, n_workers=4)

        # Then
        patches['run_serial'].assert_not_called()
        patches['run_parallel'].assert_not_called()
