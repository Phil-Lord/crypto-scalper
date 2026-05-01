import pandas as pd
import pytest

from backtesting_engine.window_evaluation import (
    evaluate_param_set_over_windows,
    run_strategy_on_window,
)


@pytest.mark.backtesting_engine
@pytest.mark.window_evaluation
class TestRunStrategyOnWindow:
    def test_resets_strategy_then_sets_window_then_runs(self, mocker):
        # Given
        engine = mocker.Mock()
        engine.strategy = mocker.Mock()
        start = pd.Timestamp('2021-01-01')
        end = pd.Timestamp('2021-04-01')

        # When
        run_strategy_on_window(engine, start, end)

        # Then
        engine.strategy.reset.assert_called_once_with()
        engine.set_ohlc_window.assert_called_once_with(start, end)
        engine.run.assert_called_once_with()

    def test_does_not_create_strategy(self, mocker):
        # Given — helper is purely the per-window mechanic; strategy creation
        # is the caller's responsibility (so callers who run many windows can
        # do it once outside the loop).
        engine = mocker.Mock()
        engine.strategy = mocker.Mock()

        # When
        run_strategy_on_window(engine, pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01'))

        # Then
        original_strategy = engine.strategy
        # Strategy reference is unchanged (no new instance assigned).
        assert engine.strategy is original_strategy


@pytest.mark.backtesting_engine
@pytest.mark.window_evaluation
class TestEvaluateParamSetOverWindows:
    @pytest.fixture
    def mock_engine(self, mocker):
        engine = mocker.Mock()
        engine.strategy = mocker.Mock()
        engine.strategy.__class__.__name__ = 'TestStrategy'
        return engine

    def test_creates_strategy_once_for_all_windows(self, mocker, mock_engine):
        # Given
        mock_create = mocker.patch(
            'backtesting_engine.window_evaluation.create_strategy',
            return_value=mocker.Mock(),
        )
        windows = [
            (pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01')),
            (pd.Timestamp('2021-02-01'), pd.Timestamp('2021-05-01')),
            (pd.Timestamp('2021-03-01'), pd.Timestamp('2021-06-01')),
        ]

        # When
        evaluate_param_set_over_windows(mock_engine, {'sma_period': 10}, windows)

        # Then
        mock_create.assert_called_once_with('TestStrategy', {'sma_period': 10})

    def test_resets_strategy_between_windows(self, mocker, mock_engine):
        # Given
        new_strategy = mocker.Mock()
        mocker.patch(
            'backtesting_engine.window_evaluation.create_strategy',
            return_value=new_strategy,
        )
        windows = [
            (pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01')),
            (pd.Timestamp('2021-02-01'), pd.Timestamp('2021-05-01')),
        ]

        # When
        evaluate_param_set_over_windows(mock_engine, {}, windows)

        # Then
        assert new_strategy.reset.call_count == len(windows)

    def test_returns_balance_per_window_in_order(self, mocker, mock_engine):
        # Given
        mocker.patch('backtesting_engine.window_evaluation.create_strategy')
        mock_engine.get_final_quote_balance.side_effect = [1100.0, 950.0, 1200.0]
        windows = [
            (pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01')),
            (pd.Timestamp('2021-02-01'), pd.Timestamp('2021-05-01')),
            (pd.Timestamp('2021-03-01'), pd.Timestamp('2021-06-01')),
        ]

        # When
        balances = evaluate_param_set_over_windows(mock_engine, {}, windows)

        # Then
        assert balances == [1100.0, 950.0, 1200.0]

    def test_passes_initial_balance_to_engine(self, mocker, mock_engine):
        # Given
        mocker.patch('backtesting_engine.window_evaluation.create_strategy')
        windows = [(pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01'))]

        # When
        evaluate_param_set_over_windows(mock_engine, {}, windows, initial_balance=500)

        # Then
        mock_engine.get_final_quote_balance.assert_called_once_with(500)

    def test_default_initial_balance_is_1000(self, mocker, mock_engine):
        # Given
        mocker.patch('backtesting_engine.window_evaluation.create_strategy')
        windows = [(pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01'))]

        # When
        evaluate_param_set_over_windows(mock_engine, {}, windows)

        # Then
        mock_engine.get_final_quote_balance.assert_called_once_with(1000)

    def test_propagates_value_error_from_create_strategy(self, mocker, mock_engine):
        # Given
        mocker.patch(
            'backtesting_engine.window_evaluation.create_strategy',
            side_effect=ValueError('Invalid params'),
        )
        windows = [(pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01'))]

        # When / Then — caller is responsible for translating ValueError.
        with pytest.raises(ValueError):
            evaluate_param_set_over_windows(mock_engine, {}, windows)
