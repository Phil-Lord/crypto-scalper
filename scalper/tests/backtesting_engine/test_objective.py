import optuna
import pandas as pd
import pytest

from backtesting_engine.objective import get_objective


@pytest.fixture()
def engine_patch(mocker):
    return mocker.patch('backtesting_engine.BacktestingEngine')


@pytest.fixture()
def strategy_manager_patch(mocker):
    return mocker.patch('backtesting_engine.objective.StrategyManager')


@pytest.mark.get_objective
def test_get_objective(engine_patch, strategy_manager_patch):
    # Given
    engine_patch.strategy.__class__.__name__ = 'TestStrategyName'
    strategy_manager_patch.get_strategy.return_value = None
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

    strategy_manager_patch().get_strategy.assert_called_once_with(
        'TestStrategyName', short_ema=9, long_ema=25)

    engine_patch.set_ohlc_window.assert_called_once_with(
        pd.Timestamp('2021-01-01 00:00:00'),
        pd.Timestamp('2021-03-31 23:59:59')
    )
    engine_patch.run.assert_called_once()
    engine_patch.get_final_quote_balance.assert_called_once_with(1000)
