import optuna
import pandas as pd
import pytest

from backtesting_engine.objective import (calculate_penalty, get_objective, suggest_parameters)


@pytest.mark.backtesting_engine
@pytest.mark.objective
class TestGetObjective:
    @pytest.fixture
    def engine_patch(self, mocker):
        ''' Mock engine with strategy and create_strategy factory. '''
        mock_new_strategy = mocker.MagicMock(name='new_strategy')
        mock_create_strategy = mocker.patch(
            'backtesting_engine.objective.create_strategy',
            return_value=mock_new_strategy
        )

        # Create the engine
        engine = mocker.patch('backtesting_engine.BacktestingEngine')

        # Use a stub class so type().__name__ returns the expected strategy name
        PrecisionTrendStrategy = type('PrecisionTrendStrategy', (), {})
        engine.strategy = PrecisionTrendStrategy()

        # Store references for assertions
        engine._mock_create_strategy = mock_create_strategy
        engine._mock_new_strategy = mock_new_strategy

        return engine

    def test_get_objective_returns_callable(self, engine_patch):
        # Given
        param_grid = {'short_ema': [1, 10], 'long_ema': [20, 30]}
        windows = [(pd.Timestamp('2021-01-01'), pd.Timestamp('2021-03-31'))]

        # When
        objective = get_objective(engine_patch, param_grid, windows)

        # Then
        assert callable(objective)

    def test_get_objective(self, engine_patch):
        # Given
        mock_create_strategy = engine_patch._mock_create_strategy

        engine_patch.set_ohlc_window.return_value = None
        engine_patch.run.return_value = None
        engine_patch.get_final_quote_balance.return_value = 1500
        engine_patch.results = pd.DataFrame({
            'signal': ['buy', 'sell', 'hold', 'buy', 'hold', 'sell', 'hold']
        })

        param_grid = {'short_ema': [1, 10], 'long_ema': [20, 30]}
        windows = [(
            pd.Timestamp('2021-01-01 00:00:00'),
            pd.Timestamp('2021-03-31 23:59:59')
        )]

        # When
        objective = get_objective(engine_patch, param_grid, windows)
        avg_return = objective(optuna.trial.FixedTrial({'short_ema': 9, 'long_ema': 25}))

        # Then
        assert isinstance(avg_return, float)

        # Verify create_strategy was called with class name and params
        mock_create_strategy.assert_called_with(
            'PrecisionTrendStrategy', {'short_ema': 9, 'long_ema': 25}
        )

        engine_patch.set_ohlc_window.assert_called_once_with(
            pd.Timestamp('2021-01-01 00:00:00'),
            pd.Timestamp('2021-03-31 23:59:59')
        )
        engine_patch.run.assert_called_once()
        engine_patch.get_final_quote_balance.assert_called_once_with(1000)

    def test_get_objective_prunes_when_config_validation_fails(self, engine_patch, mocker):
        # Given
        param_grid = {'short_ema': [1, 25], 'long_ema': [10, 30]}
        windows = [(pd.Timestamp('2021-01-01'), pd.Timestamp('2021-03-31'))]

        # Make create_strategy raise ValueError for invalid params
        engine_patch._mock_create_strategy.side_effect = ValueError('short_ema must be < long_ema')

        # When
        objective = get_objective(engine_patch, param_grid, windows)

        # Then - Config validation failure should raise TrialPruned
        with pytest.raises(optuna.TrialPruned):
            objective(optuna.trial.FixedTrial({'short_ema': 20, 'long_ema': 15}))


@pytest.mark.backtesting_engine
@pytest.mark.objective
class TestSuggestParameters:
    def test_suggest_parameters_int_range(self):
        # Given
        param_grid = {'window': [5, 20]}
        trial = optuna.trial.FixedTrial({'window': 10})

        # When
        params = suggest_parameters(trial, param_grid)

        # Then
        assert params == {'window': 10}

    def test_suggest_parameters_float_range(self):
        # Given
        param_grid = {'threshold': [0.1, 0.9]}
        trial = optuna.trial.FixedTrial({'threshold': 0.5})

        # When
        params = suggest_parameters(trial, param_grid)

        # Then
        assert params == {'threshold': 0.5}

    def test_suggest_parameters_mixed_types(self):
        # Given
        param_grid = {'window': [5, 20], 'threshold': [0.1, 0.9]}
        trial = optuna.trial.FixedTrial({'window': 10, 'threshold': 0.5})

        # When
        params = suggest_parameters(trial, param_grid)

        # Then
        assert params == {'window': 10, 'threshold': 0.5}


@pytest.mark.backtesting_engine
@pytest.mark.objective
class TestCalculatePenalty:
    @pytest.mark.parametrize(
        "trade_count, days, expected_range",
        [
            (0, 90, (0.0, 0.8)),  # No trades → penalty should be low
            (28, 90, (0.9, 1.0)),  # Around target → should approach 1.0
            (200, 90, (0.9, 1.0)),  # Above target → clamped at 1.0
            (72, 1, (0.9, 1.0)),  # 1-day window → still valid behaviour
        ]
    )
    def test_calculate_penalty_various_counts(self, trade_count, days, expected_range):
        start = pd.Timestamp("2025-01-01")
        end = start + pd.Timedelta(days=days)
        result = calculate_penalty(trade_count, start, end)
        assert expected_range[0] <= result <= expected_range[1], (
            f"Expected result in {expected_range}, got {result}"
        )

    @pytest.mark.calculate_penalty
    def test_monotonic_increase(self):
        ''' Penalty should increase monotonically as trade_count rises (up to cap). '''
        start = pd.Timestamp("2025-01-01")
        end = start + pd.Timedelta(days=90)
        results = [calculate_penalty(tc, start, end) for tc in range(0, 200, 20)]
        assert all(x <= y + 1e-6 for x, y in zip(results, results[1:])), "Penalty not monotonic"
