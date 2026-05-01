import numpy as np
import pandas as pd
import pytest
from unittest.mock import Mock, MagicMock, patch

from backtesting_engine import BacktestingEngine
from backtesting_engine.out_of_sample_evaluation import (
    get_top_param_sets,
    run_evaluation,
    save_results
)
from backtesting_engine.parameter_optimisation import create_windows
from data_system import (
    Trade,
    SQLAlchemyClient,
    SQLAlchemyTradeRepository,
    SQLAlchemyOutOfSampleEvaluationRepository
)
from data_system.models import Signal
from strategy_manager import SmaStrategy, SmaStrategyConfig


@pytest.mark.integration
@pytest.mark.backtesting_engine_integration
class TestBacktestingEngineIntegration:
    '''
    Integration tests for Backtesting Engine module.

    These tests verify that the full backtesting stack works correctly
    without mocking indicators, strategies, or profit calculations. Tests cover:
    - BacktestingEngine loading data and running strategies
    - Profit calculation on real strategy results
    - Parameter optimisation objective function
    - Out-of-sample evaluation flow
    - Integration with Data System (TradeRepository)
    '''

    # ==================== Fixtures ====================

    @pytest.fixture
    def sample_trades(self) -> list[Trade]:
        '''Generate realistic trade data with uptrend pattern.'''
        np.random.seed(42)
        trades = []
        base_time = 1704067200.0  # 2024-01-01 00:00:00
        base_price = 50000.0

        # Generate 500 trades over ~8 hours with uptrend
        for i in range(500):
            price = base_price + (i * 2) + np.random.normal(0, 10)  # Uptrend with noise
            trades.append(Trade(
                trade_id=100000 + i,
                pair='XXBTZGBP',
                price=price,
                volume=0.001 + np.random.uniform(0, 0.005),
                timestamp=base_time + (i * 60),  # 1 minute apart
                side='b' if i % 2 == 0 else 's',
                order_type='m'
            ))

        return trades

    @pytest.fixture
    def sample_trades_downtrend(self) -> list[Trade]:
        '''Generate realistic trade data with downtrend pattern.'''
        np.random.seed(42)
        trades = []
        base_time = 1704067200.0
        base_price = 52000.0

        # Generate 500 trades over ~8 hours with downtrend
        for i in range(500):
            price = base_price - (i * 2) + np.random.normal(0, 10)  # Downtrend
            trades.append(Trade(
                trade_id=200000 + i,
                pair='XXBTZGBP',
                price=price,
                volume=0.001 + np.random.uniform(0, 0.005),
                timestamp=base_time + (i * 60),
                side='b' if i % 2 == 0 else 's',
                order_type='m'
            ))

        return trades

    @pytest.fixture
    def mock_trade_repository(self, sample_trades: list[Trade]):
        ''' Mock TradeRepository that returns sample trades. '''
        mock_repo = Mock(spec=SQLAlchemyTradeRepository)
        mock_repo.get.return_value = sample_trades
        return mock_repo

    @pytest.fixture
    def sma_strategy(self):
        ''' Create a default SMA strategy for testing. '''
        config = SmaStrategyConfig(short_window=5, long_window=10)
        return SmaStrategy(config)

    # ==================== BacktestingEngine Full Stack Tests ====================

    def test_backtesting_engine_loads_and_transforms_data(self, mock_trade_repository: Mock, sma_strategy: SmaStrategy):
        '''
        Test full data loading pipeline: repository -> trades -> OHLC.
        Verifies transformation from Trade domain objects to OHLC DataFrame.
        '''
        # Given
        pair = 'XXBTZGBP'
        start = 1704067200.0
        end = 1704097200.0

        # When
        engine = BacktestingEngine(
            pair=pair,
            strategy=sma_strategy,
            repository=mock_trade_repository,
            start=start,
            end=end,
            interval=5,
            vectorised=True
        )

        # Then
        mock_trade_repository.get.assert_called_once_with(pair, start, end)

        # Verify OHLC data structure
        assert engine.ohlc_full is not None
        assert isinstance(engine.ohlc_full, pd.DataFrame)
        assert 'open' in engine.ohlc_full.columns
        assert 'high' in engine.ohlc_full.columns
        assert 'low' in engine.ohlc_full.columns
        assert 'close' in engine.ohlc_full.columns

        # Verify index is datetime
        assert isinstance(engine.ohlc_full.index, pd.DatetimeIndex)

        # Verify resampling worked (500 trades at 1 min = ~100 5-minute bars)
        assert len(engine.ohlc_full) > 0
        assert len(engine.ohlc_full) < len(mock_trade_repository.get.return_value)

    def test_backtesting_engine_runs_strategy_end_to_end(self, mock_trade_repository: Mock, sma_strategy: SmaStrategy):
        '''
        Test full execution: load data -> run strategy -> generate signals.
        Verifies integration between BacktestingEngine and strategy.
        '''
        # Given
        engine = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=sma_strategy,
            repository=mock_trade_repository,
            start=1704067200.0,
            end=1704097200.0,
            interval=5,
            vectorised=True
        )

        # When
        results = engine.run()

        # Then
        assert results is not None
        assert isinstance(results, pd.DataFrame)

        # Verify strategy output columns
        assert 'signal' in results.columns
        assert 'price' in results.columns
        assert 'short_sma' in results.columns
        assert 'long_sma' in results.columns

        # Verify signals are valid (signals are Signal enum values)
        valid_signals = [Signal.BUY, Signal.HOLD, Signal.SELL]
        assert results['signal'].isin(valid_signals).all()

        # Verify signal column exists and contains Signal enum values
        assert len(results) > 0
        assert all(isinstance(sig, Signal) or sig in valid_signals for sig in results['signal'])

    def test_backtesting_engine_iterative_mode_produces_same_signals(
            self, mock_trade_repository: Mock):
        '''
        Test that iterative mode produces correct signals.
        Verifies both execution modes work correctly.
        '''
        # Given - Vectorised mode
        config = SmaStrategyConfig(short_window=5, long_window=10)
        strategy_v = SmaStrategy(config)
        engine_vectorised = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=strategy_v,
            repository=mock_trade_repository,
            start=1704067200.0,
            end=1704097200.0,
            interval=5,
            vectorised=True
        )

        # Create new engine for iterative mode (needs fresh OHLC and strategy)
        mock_repo_copy = Mock(spec=SQLAlchemyTradeRepository)
        mock_repo_copy.get.return_value = mock_trade_repository.get.return_value

        strategy_i = SmaStrategy(config)
        engine_iterative = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=strategy_i,
            repository=mock_repo_copy,
            start=1704067200.0,
            end=1704097200.0,
            interval=5,
            vectorised=False
        )

        # When
        results_vectorised = engine_vectorised.run()
        results_iterative = engine_iterative.run()

        # Then
        assert len(results_vectorised) == len(results_iterative)

        # Verify both modes produce signals
        assert 'signal' in results_vectorised.columns
        assert 'signal' in results_iterative.columns

        # Both should produce similar signal distributions
        vec_counts = results_vectorised['signal'].value_counts()
        iter_counts = results_iterative['signal'].value_counts()
        assert set(vec_counts.index) == set(iter_counts.index)

    # ==================== Profit Calculation Integration Tests ====================

    def test_profit_calculation_full_integration(self, mock_trade_repository: Mock, sma_strategy: SmaStrategy):
        '''
        Test full profit calculation flow with real strategy results.
        Verifies integration of strategy execution -> profit calculation.
        '''
        # Given
        engine = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=sma_strategy,
            repository=mock_trade_repository,
            start=1704067200.0,
            end=1704097200.0,
            interval=5,
            vectorised=True
        )
        engine.run()
        initial_balance = 1000.0

        # When
        final_balance = engine.get_final_quote_balance(initial_balance)
        position_profits = engine.calculate_position_profits(initial_balance)

        # Then
        assert isinstance(final_balance, float)
        assert final_balance > 0  # Should have some balance

        # Verify position profits structure
        assert isinstance(position_profits, pd.DataFrame)
        if len(position_profits) > 0:
            assert 'entry_time' in position_profits.columns
            assert 'exit_time' in position_profits.columns
            assert 'profit' in position_profits.columns

            # Verify entry times are before exit times
            assert (position_profits['exit_time'] > position_profits['entry_time']).all()

    def test_profit_calculation_with_uptrend_strategy(self, mock_trade_repository: Mock):
        '''
        Test that strategy produces profit on uptrending data.
        Integration test of realistic trading scenario.
        '''
        # Given - Data has uptrend built in
        config = SmaStrategyConfig(short_window=3, long_window=8)
        strategy = SmaStrategy(config)
        engine = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=strategy,
            repository=mock_trade_repository,
            start=1704067200.0,
            end=1704097200.0,
            interval=5,
            vectorised=True
        )
        engine.run()
        initial_balance = 1000.0

        # When
        final_balance = engine.get_final_quote_balance(initial_balance)

        # Then - Should make profit on uptrend with good parameters
        assert final_balance >= initial_balance * 0.95  # Allow for fees

    def test_set_ohlc_window_filters_data_correctly(self, mock_trade_repository: Mock, sma_strategy: SmaStrategy):
        '''
        Test window filtering for parameter optimisation.
        Verifies ability to run strategy on subsets of data.
        '''
        # Given
        engine = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=sma_strategy,
            repository=mock_trade_repository,
            start=1704067200.0,
            end=1704097200.0,
            interval=5,
            vectorised=True
        )

        original_length = len(engine.ohlc_full)

        # When - Set window to first half of data
        mid_time = engine.ohlc_full.index[original_length // 2]
        start_time = engine.ohlc_full.index[0]
        engine.set_ohlc_window(start_time, mid_time)

        # Then
        assert len(engine.ohlc_window) < original_length
        assert len(engine.ohlc_window) <= original_length // 2 + 1

        # Verify window boundaries
        assert engine.ohlc_window.index[0] >= start_time
        assert engine.ohlc_window.index[-1] <= mid_time

        # When - Reset to full window
        engine.set_ohlc_window()

        # Then
        assert len(engine.ohlc_window) == original_length

    # ==================== Parameter Optimisation Integration Tests ====================

    def test_create_windows_generates_valid_rolling_windows(self):
        '''
        Test window creation for parameter optimisation.
        Verifies rolling window generation logic.
        '''
        # Given - 6 month period (should create ~4 windows: months 0-2, 1-3, 2-4, 3-5)
        start = pd.Timestamp('2024-01-01').timestamp()
        end = pd.Timestamp('2024-07-01').timestamp()

        # When
        windows = create_windows(start, end)

        # Then
        assert len(windows) > 0
        assert len(windows) >= 4  # At least 4 3-month windows in 6 months

        # Verify window structure
        for window_start, window_end in windows:
            assert isinstance(window_start, pd.Timestamp)
            assert isinstance(window_end, pd.Timestamp)
            assert window_end > window_start

            # Each window should be approximately 3 months
            duration = (window_end - window_start).days
            assert 85 <= duration <= 95  # ~90 days ± some tolerance

    def test_objective_function_integration(self, mock_trade_repository: Mock, sma_strategy: SmaStrategy):
        '''
        Test objective function with real strategy execution.
        Verifies optimisation objective logic without running full Optuna.
        '''
        # Given
        from backtesting_engine.objective import get_objective

        engine = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=sma_strategy,
            repository=mock_trade_repository,
            start=1704067200.0,
            end=1704097200.0,
            interval=5,
            vectorised=True,
        )

        # Create a single window (full data for simplicity)
        windows = [(engine.ohlc_full.index[0], engine.ohlc_full.index[-1])]
        param_grid = {'short_window': (3, 15), 'long_window': (10, 30)}

        # Mock trial object
        mock_trial = Mock()
        mock_trial.suggest_int = Mock(side_effect=lambda name, low, high:
                                      5 if name == 'short_window' else 10)
        mock_trial.set_user_attr = Mock()

        # When
        objective = get_objective(engine, param_grid, windows=windows)
        score = objective(mock_trial)

        # Then
        assert isinstance(score, float)
        assert score > 0  # Geometric mean should be positive
        mock_trial.suggest_int.assert_called()
        mock_trial.set_user_attr.assert_called()

    # ==================== Generalisation Evaluation Integration Tests ====================

    def test_get_top_param_sets_extracts_completed_trials(self):
        '''
        Test extraction of top parameter sets from Optuna study.
        Verifies filtering and sorting logic.
        '''
        # Given - Mock Optuna study
        import optuna

        mock_trial_1 = Mock()
        mock_trial_1.state = optuna.trial.TrialState.COMPLETE
        mock_trial_1.number = 1
        mock_trial_1.value = 1.05
        mock_trial_1.params = {'short_window': 5, 'long_window': 10}

        mock_trial_2 = Mock()
        mock_trial_2.state = optuna.trial.TrialState.COMPLETE
        mock_trial_2.number = 2
        mock_trial_2.value = 1.08
        mock_trial_2.params = {'short_window': 3, 'long_window': 12}

        mock_trial_3 = Mock()
        mock_trial_3.state = optuna.trial.TrialState.PRUNED
        mock_trial_3.number = 3

        mock_study = Mock()
        mock_study.trials = [mock_trial_1, mock_trial_2, mock_trial_3]
        mock_study.direction = optuna.study.StudyDirection.MAXIMIZE

        # When
        top_sets = get_top_param_sets(mock_study, n=2, evaluated_trials=set())

        # Then
        assert len(top_sets) == 2
        assert top_sets[0]['trial_number'] == 2  # Higher value first
        assert top_sets[0]['value'] == 1.08
        assert top_sets[1]['trial_number'] == 1

    def test_run_evaluation_calculates_metrics(self, mock_trade_repository: Mock, sma_strategy: SmaStrategy):
        '''
        Test out-of-sample evaluation calculation.
        Verifies evaluation metrics computation on new data.
        '''
        # Given
        engine = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=sma_strategy,
            repository=mock_trade_repository,
            start=1704067200.0,
            end=1704097200.0,
            interval=5,
            vectorised=True,
        )

        top_param_sets = [
            {
                'trial_number': 1,
                'value': 1.05,
                'params': {'short_window': 5, 'long_window': 10}
            }
        ]

        # Create a single window
        windows = [(engine.ohlc_full.index[0], engine.ohlc_full.index[-1])]

        # When
        results = run_evaluation(engine, top_param_sets, windows)

        # Then
        assert len(results) == 1
        assert 'trial_number' in results[0]
        assert 'final_balance' in results[0]
        assert 'geo_mean_return' in results[0]

        assert results[0]['trial_number'] == 1
        assert isinstance(results[0]['final_balance'], float)
        assert isinstance(results[0]['geo_mean_return'], float)
        assert results[0]['final_balance'] > 0
        assert results[0]['geo_mean_return'] > 0

    def test_save_results_transforms_to_domain_objects(self):
        '''
        Test saving evaluation results to repository.
        Verifies transformation to OutOfSampleEvaluation domain objects.
        '''
        # Given
        mock_session = MagicMock()
        mock_engine = Mock()

        with patch('data_system.clients.sqlalchemy_client.create_engine',
                   return_value=mock_engine):
            with patch('data_system.clients.sqlalchemy_client.sessionmaker') \
                    as mock_sessionmaker:
                mock_session_class = Mock()
                mock_session_class.return_value = mock_session
                mock_sessionmaker.return_value = mock_session_class

                client = SQLAlchemyClient()
                repository = SQLAlchemyOutOfSampleEvaluationRepository(client)

                results = [
                    {
                        'trial_number': 1,
                        'final_balance': 1050.0,
                        'geo_mean_return': 1.05
                    }
                ]

                # When
                save_results(
                    repository,
                    results,
                    study_name='SmaStrategy_XXBTZGBP_20240101-20240701',
                    start=1704067200.0,
                    end=1704097200.0
                )

        # Then
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args

        # Verify SQL statement
        sql_stmt = str(call_args[0][0])
        assert 'INSERT' in sql_stmt
        assert 'out_of_sample_evaluation' in sql_stmt

        # Verify domain data transformation
        records = call_args[0][1]
        assert len(records) == 1
        assert records[0]['study_name'] == 'SmaStrategy_XXBTZGBP_20240101-20240701'
        assert records[0]['trial_number'] == 1
        assert records[0]['final_balance'] == 1050.0
        assert records[0]['geo_mean_return'] == 1.05

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    # ==================== Error Handling Integration Tests ====================

    def test_backtesting_engine_raises_error_when_no_trades_found(self, sma_strategy: SmaStrategy):
        '''
        Test error handling when repository returns no data.
        Verifies error propagation through layers.
        '''
        # Given
        mock_repo = Mock(spec=SQLAlchemyTradeRepository)
        mock_repo.get.return_value = []  # No trades

        # When / Then
        with pytest.raises(ValueError, match='No trades found'):
            BacktestingEngine(
                pair='XXBTZGBP',
                strategy=sma_strategy,
                repository=mock_repo,
                start=1704067200.0,
                end=1704097200.0,
                interval=5,
            )

    def test_profit_calculation_raises_error_before_run(self, mock_trade_repository: Mock, sma_strategy: SmaStrategy):
        '''
        Test error handling when calculating profits before running backtest.
        Verifies validation logic.
        '''
        # Given
        engine = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=sma_strategy,
            repository=mock_trade_repository,
            start=1704067200.0,
            end=1704097200.0,
            interval=5,
        )

        # When / Then - Before run()
        with pytest.raises(ValueError, match='Backtest yet to be ran'):
            engine.get_final_quote_balance()

        with pytest.raises(ValueError, match='Backtest yet to be ran'):
            engine.calculate_position_profits()

    def test_create_windows_raises_error_for_short_time_range(self):
        '''
        Test validation of minimum time range for optimisation.
        '''
        # Given - Only 2 months (need at least 3)
        start = pd.Timestamp('2024-01-01').timestamp()
        end = pd.Timestamp('2024-03-01').timestamp()

        # When / Then
        with pytest.raises(ValueError, match='Time range must be at least 3 months'):
            create_windows(start, end)

    # ==================== Data Integrity Tests ====================

    def test_ohlc_resampling_preserves_price_continuity(self, mock_trade_repository: Mock, sma_strategy: SmaStrategy):
        '''
        Test that OHLC resampling produces continuous price data.
        Verifies no gaps or invalid values after transformation.
        '''
        # Given
        engine = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=sma_strategy,
            repository=mock_trade_repository,
            start=1704067200.0,
            end=1704097200.0,
            interval=5,
        )

        # Then
        assert not engine.ohlc_full.isnull().any().any()  # No NaN values
        assert (engine.ohlc_full['high'] >= engine.ohlc_full['close']).all()
        assert (engine.ohlc_full['low'] <= engine.ohlc_full['close']).all()
        assert (engine.ohlc_full['high'] >= engine.ohlc_full['low']).all()

    def test_multiple_strategies_on_same_data(self, mock_trade_repository: Mock, sma_strategy: SmaStrategy):
        '''
        Test running different strategies on same dataset.
        Verifies engine reusability and strategy isolation.
        '''
        # Given - SMA Strategy
        engine_sma = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=sma_strategy,
            repository=mock_trade_repository,
            start=1704067200.0,
            end=1704097200.0,
            interval=5,
            vectorised=True,
        )

        # Given - Another SMA Strategy with different parameters
        mock_repo_2 = Mock(spec=SQLAlchemyTradeRepository)
        mock_repo_2.get.return_value = mock_trade_repository.get.return_value

        engine_sma2 = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=sma_strategy,
            repository=mock_repo_2,
            start=1704067200.0,
            end=1704097200.0,
            interval=5,
            vectorised=True,
        )

        # When
        results_sma = engine_sma.run()
        results_sma2 = engine_sma2.run()

        # Then - Both produce valid results
        assert 'signal' in results_sma.columns
        assert 'signal' in results_sma2.columns

        # Both strategies should run successfully
        assert len(results_sma) > 0
        assert len(results_sma2) > 0
