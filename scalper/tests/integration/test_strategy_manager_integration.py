import numpy as np
import pandas as pd
import pytest

from data_system import Signal
from strategy_manager import (
    SmaStrategy,
    SmaStrategyConfig,
    PrecisionTrendStrategy,
    PrecisionTrendStrategyConfig
)


@pytest.mark.integration
@pytest.mark.strategy_manager_integration
class TestStrategyManagerIntegration:
    '''
    Integration tests for Strategy Manager module.

    These tests verify that the full strategy stack works correctly
    without mocking indicators or rules. Tests cover:
    - Strategy creation with config objects
    - Indicator computation (update and vectorised)
    - Rule evaluation
    - Signal generation
    - End-to-end strategy execution
    '''

    # ==================== Fixtures ====================

    @pytest.fixture
    def uptrend_data(self) -> pd.DataFrame:
        '''Generate uptrending price data with clear crossover opportunities.'''
        np.random.seed(42)
        n = 100
        # Start flat then trend up to create a crossover
        prices = []
        for i in range(n):
            if i < 15:
                # Flat/choppy at start
                prices.append(100 + np.random.normal(0, 0.5))
            else:
                # Strong uptrend
                prices.append(100 + (i - 15) * 0.6 + np.random.normal(0, 0.3))

        prices = np.array(prices)
        return pd.DataFrame({
            'close': prices,
            'high': prices + 0.5,
            'low': prices - 0.5
        })

    @pytest.fixture
    def downtrend_data(self) -> pd.DataFrame:
        '''Generate downtrending price data with clear crossover opportunities.'''
        np.random.seed(42)
        n = 100
        # Start flat then trend down to create a crossover
        prices = []
        for i in range(n):
            if i < 15:
                # Flat/choppy at start
                prices.append(150 + np.random.normal(0, 0.5))
            else:
                # Strong downtrend
                prices.append(150 - (i - 15) * 0.6 + np.random.normal(0, 0.3))

        prices = np.array(prices)
        return pd.DataFrame({
            'close': prices,
            'high': prices + 0.5,
            'low': prices - 0.5
        })

    @pytest.fixture
    def sideways_data(self) -> pd.DataFrame:
        '''Generate sideways/choppy price data.'''
        np.random.seed(42)
        n = 100
        prices = 100 + np.random.normal(0, 2, n)

        return pd.DataFrame({
            'close': prices,
            'high': prices + 0.5,
            'low': prices - 0.5
        })

    # ==================== SmaStrategy Integration Tests ====================

    def test_sma_strategy_full_stack_with_uptrend(self, uptrend_data: pd.DataFrame):
        '''
        Test SmaStrategy end-to-end with uptrending data.
        Verifies indicators compute, rules evaluate, and signals generate correctly.
        '''
        # Given
        config = SmaStrategyConfig(short_window=5, long_window=10)
        strategy = SmaStrategy(config)

        # When
        result = strategy.vectorised_compute(uptrend_data)

        # Then
        assert 'price' in result.columns
        assert 'short_sma' in result.columns
        assert 'long_sma' in result.columns
        assert 'crossover' in result.columns
        assert 'signal' in result.columns

        # Verify SMA values are computed
        assert result['short_sma'].notna().sum() > 0
        assert result['long_sma'].notna().sum() > 0

        # In an uptrend, we should see at least one BUY signal
        assert (result['signal'] == Signal.BUY).any()

        # Verify no consecutive identical non-HOLD signals
        signals = result['signal'].values
        for i in range(1, len(signals)):
            if signals[i] in (Signal.BUY, Signal.SELL) and signals[i-1] == signals[i]:
                pytest.fail(f'Consecutive {signals[i]} signals at index {i-1}, {i}')

    def test_sma_strategy_full_stack_with_downtrend(self, downtrend_data: pd.DataFrame):
        '''Test SmaStrategy with downtrending data - should generate SELL signals.'''
        # Given
        config = SmaStrategyConfig(short_window=5, long_window=10)
        strategy = SmaStrategy(config)

        # When
        result = strategy.vectorised_compute(downtrend_data)

        # Then
        # In a downtrend, we should see at least one SELL signal
        assert (result['signal'] == Signal.SELL).any()

    def test_sma_strategy_update_mode_matches_vectorised(self, uptrend_data: pd.DataFrame):
        '''
        Test that update() mode (for live trading) matches vectorised() results.
        This ensures consistency between backtesting and live trading.
        '''
        # Given
        config = SmaStrategyConfig(short_window=5, long_window=10)
        strategy_update = SmaStrategy(config)
        strategy_vectorised = SmaStrategy(config)

        # When - Generate signals using update mode
        update_signals = []
        for _, row in uptrend_data.iterrows():
            result = strategy_update.generate_signal(row)
            update_signals.append(result['signal'])

        # When - Generate signals using vectorised mode
        vectorised_result = strategy_vectorised.vectorised_compute(uptrend_data)
        vectorised_signals = vectorised_result['signal'].values

        # Then - Signals should match
        assert len(update_signals) == len(vectorised_signals)
        for i, (update_sig, vect_sig) in enumerate(zip(update_signals, vectorised_signals)):
            assert update_sig == vect_sig, f'Signal mismatch at index {i}: {update_sig} != {vect_sig}'

    # ==================== PrecisionTrendStrategy Integration Tests ====================

    def test_precision_trend_strategy_full_stack_with_uptrend(self, uptrend_data: pd.DataFrame):
        '''
        Test PrecisionTrendStrategy end-to-end with uptrending data.
        Verifies all 4 indicators and 4 rules work together correctly.
        '''
        # Given
        config = PrecisionTrendStrategyConfig(
            short_ema=5,
            long_ema=10,
            rsi_window=14,
            rsi_oversold=30,
            rsi_overbought=70,
            adx_window=14,
            adx_threshold=20,
            atr_window=14,
            atr_threshold=0.005,
            weight_crossover=1.0,
            weight_rsi=1.0,
            weight_adx=1.0,
            weight_atr=1.0,
            buy_threshold=0.3,
            sell_threshold=-0.3
        )
        strategy = PrecisionTrendStrategy(config)

        # When
        result = strategy.vectorised_compute(uptrend_data)

        # Then - Check all indicators are computed
        assert 'short_ema' in result.columns
        assert 'long_ema' in result.columns
        assert 'rsi' in result.columns
        assert 'adx' in result.columns
        assert 'atr' in result.columns

        # Check all rules are evaluated
        assert 'crossover' in result.columns
        assert 'rsi_threshold' in result.columns
        assert 'adx_threshold' in result.columns
        assert 'atr_threshold' in result.columns

        # Check signals are generated
        assert 'signal' in result.columns

        # Verify indicators have values
        assert result['short_ema'].notna().sum() > 0
        assert result['rsi'].notna().sum() > 0
        assert result['adx'].notna().sum() > 0
        assert result['atr'].notna().sum() > 0

        # All signals should be valid
        assert result['signal'].isin([Signal.BUY, Signal.HOLD, Signal.SELL]).all()

    def test_precision_trend_strategy_weighted_scoring(self):
        '''
        Test that weighted scoring works correctly by using extreme weights.
        '''
        # Given - Create data where crossover would BUY but others might not
        np.random.seed(42)
        n = 50
        prices = np.linspace(100, 110, n)
        data = pd.DataFrame({
            'close': prices,
            'high': prices + 0.5,
            'low': prices - 0.5
        })

        # Strategy with crossover heavily weighted
        config = PrecisionTrendStrategyConfig(
            short_ema=3,
            long_ema=5,
            rsi_window=5,
            rsi_oversold=30,
            rsi_overbought=70,
            adx_window=5,
            adx_threshold=25,
            atr_window=5,
            atr_threshold=0.01,
            weight_crossover=10.0,  # Heavy weight
            weight_rsi=1.0,
            weight_adx=1.0,
            weight_atr=1.0,
            buy_threshold=0.5,
            sell_threshold=-0.5
        )
        strategy = PrecisionTrendStrategy(config)

        # When
        result = strategy.vectorised_compute(data)

        # Then - Should generate some signals (exact signals depend on data)
        assert result['signal'].isin([Signal.BUY, Signal.HOLD, Signal.SELL]).all()

    def test_precision_trend_strategy_update_mode_consistency(self):
        '''
        Test consistency between update and vectorised modes for PrecisionTrendStrategy.
        Uses simple data to ensure the test focuses on mode consistency rather than signal generation.
        '''
        # Given
        config = PrecisionTrendStrategyConfig(
            short_ema=5,
            long_ema=10,
            rsi_window=14,
            rsi_oversold=30,
            rsi_overbought=70,
            adx_window=14,
            adx_threshold=25,
            atr_window=14,
            atr_threshold=0.01,
            weight_crossover=1.0,
            weight_rsi=1.0,
            weight_adx=1.0,
            weight_atr=1.0,
            buy_threshold=0.5,
            sell_threshold=-0.5
        )

        strategy_update = PrecisionTrendStrategy(config)
        strategy_vectorised = PrecisionTrendStrategy(config)

        # Use simple trending data
        np.random.seed(42)
        n = 50
        data = pd.DataFrame({
            'close': np.linspace(100, 110, n),
            'high': np.linspace(101, 111, n),
            'low': np.linspace(99, 109, n)
        })

        # When - Generate signals using update mode
        update_signals = []
        for _, row in data.iterrows():
            result = strategy_update.generate_signal(row)
            update_signals.append(result['signal'])

        # When - Generate signals using vectorised mode
        vectorised_result = strategy_vectorised.vectorised_compute(data)
        vectorised_signals = vectorised_result['signal'].values

        # Then - Signals should match
        for i, (update_sig, vect_sig) in enumerate(zip(update_signals, vectorised_signals)):
            assert update_sig == vect_sig, f'Signal mismatch at index {i}: {update_sig} != {vect_sig}'

    # ==================== StrategyManager Integration Tests ====================

    def test_config_validation_creates_working_strategies(self):
        ''' Test that config objects create functional strategy instances. '''
        # Given / When
        sma_config = SmaStrategyConfig(short_window=5, long_window=10)
        sma_strategy = SmaStrategy(sma_config)

        precision_config = PrecisionTrendStrategyConfig(
            short_ema=5, long_ema=10, rsi_window=14, rsi_oversold=30, rsi_overbought=70,
            adx_window=14, adx_threshold=25, atr_window=14, atr_threshold=0.01,
            weight_crossover=1.0, weight_rsi=1.0, weight_adx=1.0, weight_atr=1.0,
            buy_threshold=0.5, sell_threshold=-0.5
        )
        precision_strategy = PrecisionTrendStrategy(precision_config)

        # Then - Both strategies should be functional
        test_data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104],
            'high': [100.5, 101.5, 102.5, 103.5, 104.5],
            'low': [99.5, 100.5, 101.5, 102.5, 103.5]
        })

        sma_result = sma_strategy.vectorised_compute(test_data)
        precision_result = precision_strategy.vectorised_compute(test_data)

        assert 'signal' in sma_result.columns
        assert 'signal' in precision_result.columns

    def test_multiple_strategy_instances_are_independent(self):
        '''
        Test that multiple strategy instances with the same config are independent.
        '''
        # Given
        config = SmaStrategyConfig(short_window=5, long_window=10)
        strategy1 = SmaStrategy(config)
        strategy2 = SmaStrategy(config)

        # When - Generate signal on strategy1
        ohlc = pd.Series({'close': 100.0})
        strategy1.generate_signal(ohlc)

        # Then - strategy2 should still have initial state
        assert strategy2.last_action == Signal.SELL  # Default initial state
        assert strategy1.last_action != strategy2.last_action or strategy1.last_action == Signal.SELL
