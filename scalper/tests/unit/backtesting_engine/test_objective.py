import optuna
import pandas as pd
import pytest

from backtesting_engine.objective import (
    calculate_penalty,
    get_objective,
    suggest_parameters,
    parameters_violate_constraints
)


@pytest.mark.backtesting_engine
@pytest.mark.objective
class TestGetObjective:
    @pytest.fixture
    def engine_patch(self, mocker):
        ''' Mock engine with strategy and config setup. '''
        # Create simple callable mocks that don't try to use args as spec
        mock_config_instance = mocker.MagicMock(name='config_instance')
        mock_config_class = mocker.MagicMock(name='ConfigClass', return_value=mock_config_instance)

        mock_new_strategy = mocker.MagicMock(name='new_strategy')
        mock_strategy_class = mocker.MagicMock(name='StrategyClass', return_value=mock_new_strategy)

        # Create the engine
        engine = mocker.patch('backtesting_engine.BacktestingEngine')

        # Set up current strategy and config
        mock_current_config = mocker.MagicMock(name='current_config')
        mock_current_strategy = mocker.MagicMock(name='current_strategy')
        mock_current_strategy.config = mock_current_config
        engine.strategy = mock_current_strategy

        # Mock type() to return our mock classes when called on the mocks
        original_type = type

        def mock_type(obj):
            if obj is mock_current_config:
                return mock_config_class
            elif obj is mock_current_strategy:
                return mock_strategy_class
            return original_type(obj)

        mocker.patch('backtesting_engine.objective.type', side_effect=mock_type)

        # Store references for assertions
        engine._mock_config_class = mock_config_class
        engine._mock_strategy_class = mock_strategy_class
        engine._mock_new_strategy = mock_new_strategy

        return engine

    def test_get_objective_returns_callable(self, engine_patch):
        # Given
        param_grid = {'short_ema': [1, 10], 'long_ema': [20, 30]}
        windows = [(pd.Timestamp('2021-01-01'), pd.Timestamp('2021-03-31'))]

        # When
        objective = get_objective(engine_patch, param_grid, None, windows)

        # Then
        assert callable(objective)

    def test_get_objective(self, engine_patch):
        # Given
        config_class = engine_patch._mock_config_class
        strategy_class = engine_patch._mock_strategy_class

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
        objective = get_objective(engine_patch, param_grid, None, windows)
        avg_return = objective(optuna.trial.FixedTrial({'short_ema': 9, 'long_ema': 25}))

        # Then
        assert isinstance(avg_return, float)

        # Verify config was created with the right parameters
        config_class.assert_called_with(short_ema=9, long_ema=25)

        # Verify strategy was created with new config
        assert strategy_class.call_count == 1

        engine_patch.set_ohlc_window.assert_called_once_with(
            pd.Timestamp('2021-01-01 00:00:00'),
            pd.Timestamp('2021-03-31 23:59:59')
        )
        engine_patch.run.assert_called_once()
        engine_patch.get_final_quote_balance.assert_called_once_with(1000)

    def test_get_objective_prunes_when_constraints_violated(self, engine_patch):
        # Given
        param_grid = {'short_ema': [1, 25], 'long_ema': [10, 30]}
        windows = [(pd.Timestamp('2021-01-01'), pd.Timestamp('2021-03-31'))]
        constraints = [lambda params: params['short_ema']
                       < params['long_ema']]  # short must be < long

        # When
        objective = get_objective(engine_patch, param_grid, constraints, windows)

        # Then - Violating constraint should raise TrialPruned
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
class TestParametersViolateConstraints:
    def test_no_constraints_returns_false(self):
        # Given
        params = {'short_ema': 9, 'long_ema': 25}

        # When
        result = parameters_violate_constraints(None, params)

        # Then
        assert result is False

    def test_constraints_satisfied_returns_false(self):
        # Given
        params = {'short_ema': 9, 'long_ema': 25}
        constraints = [lambda p: p['short_ema'] < p['long_ema']]

        # When
        result = parameters_violate_constraints(constraints, params)

        # Then
        assert result is False

    def test_constraints_violated_returns_true(self):
        # Given
        params = {'short_ema': 25, 'long_ema': 9}
        constraints = [lambda p: p['short_ema'] < p['long_ema']]

        # When
        result = parameters_violate_constraints(constraints, params)

        # Then
        assert result is True


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
