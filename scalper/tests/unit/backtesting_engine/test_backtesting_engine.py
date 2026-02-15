import pandas as pd
import pytest

from backtesting_engine.backtesting_engine import BacktestingEngine
from data_system.models.trade_model import Trade


@pytest.mark.backtesting_engine
class TestBacktestingEngine:
    @pytest.fixture
    def sample_trades(self) -> list[Trade]:
        return [
            Trade(
                trade_id=1,
                pair='XXBTZGBP',
                price=100.0,
                volume=1.0,
                timestamp=1609459200.0,  # 2021-01-01 00:00:00
                side='b',
                order_type='m'
            ),
            Trade(
                trade_id=2,
                pair='XXBTZGBP',
                price=101.0,
                volume=1.0,
                timestamp=1609459260.0,  # 2021-01-01 00:01:00
                side='s',
                order_type='m'
            ),
            Trade(
                trade_id=3,
                pair='XXBTZGBP',
                price=102.0,
                volume=1.0,
                timestamp=1609459320.0,  # 2021-01-01 00:02:00
                side='b',
                order_type='m'
            ),
        ]

    @pytest.fixture
    def mock_repository(self, mocker, sample_trades):
        repo = mocker.Mock()
        repo.get.return_value = sample_trades
        return repo

    @pytest.fixture
    def mock_strategy(self, mocker):
        '''Mock strategy with vectorised_compute.'''
        strategy = mocker.Mock()
        strategy.__class__.__name__ = 'TestStrategy'
        strategy.vectorised_compute.return_value = pd.DataFrame({
            'signal': ['hold', 'buy', 'sell']
        })
        strategy.generate_signal.return_value = {'signal': 'hold'}
        return strategy

    @pytest.mark.run
    def test_run_vectorised_mode(self, mock_repository, mock_strategy):
        # Given
        engine = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=mock_strategy,
            repository=mock_repository,
            vectorised=True
        )

        # When
        results = engine.run()

        # Then
        assert mock_strategy.vectorised_compute.called
        assert 'signal' in results.columns
        assert len(results) == 3

    @pytest.mark.run
    def test_run_non_vectorised_mode(self, mock_repository, mock_strategy):
        # Given
        engine = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=mock_strategy,
            repository=mock_repository,
            vectorised=False
        )

        # When
        results = engine.run()

        # Then
        assert mock_strategy.generate_signal.called
        assert mock_strategy.vectorised_compute.call_count == 0
        assert 'signal' in results.columns
        assert len(results) == 3

    @pytest.mark.set_ohlc_window
    def test_set_ohlc_window_with_both_args(self, mock_repository, mock_strategy):
        # Given
        engine = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=mock_strategy,
            repository=mock_repository
        )
        start = pd.Timestamp('2021-01-01 00:00:00')
        end = pd.Timestamp('2021-01-01 00:02:00')

        # When
        engine.set_ohlc_window(start, end)

        # Then
        assert len(engine.ohlc_window) == 3
        assert engine.ohlc_window.index[0] == start
        assert engine.ohlc_window.index[-1] == end

    @pytest.mark.set_ohlc_window
    def test_set_ohlc_window_with_no_args(self, mock_repository, mock_strategy):
        # Given
        engine = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=mock_strategy,
            repository=mock_repository
        )
        full_length = len(engine.ohlc_full)

        # When
        engine.set_ohlc_window()

        # Then
        assert len(engine.ohlc_window) == full_length
        pd.testing.assert_frame_equal(engine.ohlc_window, engine.ohlc_full)

    @pytest.mark.set_ohlc_window
    def test_set_ohlc_window_with_only_start(self, mock_repository, mock_strategy):
        # Given
        engine = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=mock_strategy,
            repository=mock_repository
        )
        start = pd.Timestamp('2021-01-01 00:01:00')

        # When
        engine.set_ohlc_window(start=start)

        # Then - Should use full window when end is None
        pd.testing.assert_frame_equal(engine.ohlc_window, engine.ohlc_full)

    @pytest.mark.calculate_position_profits
    def test_calculate_position_profits_before_run_raises_error(self, mock_repository, mock_strategy):
        # Given
        engine = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=mock_strategy,
            repository=mock_repository
        )

        # When / Then
        with pytest.raises(ValueError, match='Backtest yet to be ran'):
            engine.calculate_position_profits()

    @pytest.mark.get_final_quote_balance
    def test_get_final_quote_balance_before_run_raises_error(self, mock_repository, mock_strategy):
        # Given
        engine = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=mock_strategy,
            repository=mock_repository
        )

        # When / Then
        with pytest.raises(ValueError, match='Backtest yet to be ran'):
            engine.get_final_quote_balance()

    @pytest.mark.load_ohlc_data
    def test_load_ohlc_data_with_no_trades_raises_error(self, mock_strategy, mocker):
        # Given
        mock_repo = mocker.Mock()
        mock_repo.get.return_value = []

        # When / Then
        with pytest.raises(ValueError, match='No trades found'):
            BacktestingEngine(
                pair='XXBTZGBP',
                strategy=mock_strategy,
                repository=mock_repo
            )

    @pytest.mark.load_ohlc_data
    def test_load_ohlc_data_resamples_correctly(self, mock_repository, mock_strategy, sample_trades):
        # Given / When
        engine = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=mock_strategy,
            repository=mock_repository,
            interval=1
        )

        # Then
        assert len(engine.ohlc_full) == 3
        assert 'open' in engine.ohlc_full.columns
        assert 'high' in engine.ohlc_full.columns
        assert 'low' in engine.ohlc_full.columns
        assert 'price' in engine.ohlc_full.columns  # renamed from 'close'

    @pytest.mark.load_ohlc_data
    def test_load_ohlc_data_with_custom_interval(self, mock_strategy, sample_trades, mocker):
        # Given
        mock_repo = mocker.Mock()
        mock_repo.get.return_value = sample_trades

        # When
        engine = BacktestingEngine(
            pair='XXBTZGBP',
            strategy=mock_strategy,
            repository=mock_repo,
            interval=2  # 2-minute intervals
        )

        # Then
        # 3 trades over 2 minutes should resample to 2 rows (0-2min, 2-4min)
        assert len(engine.ohlc_full) == 2
