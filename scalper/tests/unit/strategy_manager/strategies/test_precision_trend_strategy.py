import numpy as np
import pandas as pd
import pytest
from unittest.mock import Mock

from data_system.models.bot_tick_model import Signal
from strategy_manager.strategies.precision_trend_strategy import PrecisionTrendStrategy
from strategy_manager.strategies.precision_trend_strategy_config import PrecisionTrendStrategyConfig


@pytest.mark.strategy_manager
@pytest.mark.strategies
@pytest.mark.precision_trend_strategy
class TestPrecisionTrendStrategy:
    @pytest.fixture
    def strategy(self) -> PrecisionTrendStrategy:
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
        return PrecisionTrendStrategy(config)

    def test_initialisation_registers_all_indicators_and_rules(self, strategy: PrecisionTrendStrategy):
        assert 'short_ema' in strategy.indicators
        assert 'long_ema' in strategy.indicators
        assert 'rsi' in strategy.indicators
        assert 'adx' in strategy.indicators
        assert 'atr' in strategy.indicators

        assert 'crossover' in strategy.rules
        assert 'rsi_threshold' in strategy.rules
        assert 'adx_threshold' in strategy.rules
        assert 'atr_threshold' in strategy.rules

    def test_initialisation_normalises_weights(self):
        # Given
        config = PrecisionTrendStrategyConfig(
            short_ema=5, long_ema=10, rsi_window=14, rsi_oversold=30, rsi_overbought=70,
            adx_window=14, adx_threshold=25, atr_window=14, atr_threshold=0.01,
            weight_crossover=2.0, weight_rsi=2.0, weight_adx=2.0, weight_atr=2.0,
            buy_threshold=0.5, sell_threshold=-0.5
        )
        strategy = PrecisionTrendStrategy(config)

        # When / Then - Total should sum to 1.0
        total = (strategy.weight_crossover + strategy.weight_rsi +
                 strategy.weight_adx + strategy.weight_atr)
        assert abs(total - 1.0) < 1e-6

    def test_generate_signal_returns_buy_when_score_above_threshold(self, strategy: PrecisionTrendStrategy):
        # Given - All rules return BUY
        rule_results = {
            'crossover': Signal.BUY,
            'rsi_threshold': Signal.BUY,
            'adx_threshold': Signal.BUY,
            'atr_threshold': Signal.BUY
        }

        # When
        signal = strategy._generate_signal(rule_results)

        # Then
        assert signal == Signal.BUY  # Score = 1.0, above buy_threshold (0.5)

    def test_generate_signal_returns_sell_when_score_below_threshold(self, strategy: PrecisionTrendStrategy):
        # Given - All rules return SELL
        rule_results = {
            'crossover': Signal.SELL,
            'rsi_threshold': Signal.SELL,
            'adx_threshold': Signal.SELL,
            'atr_threshold': Signal.SELL
        }

        # When
        signal = strategy._generate_signal(rule_results)

        # Then
        assert signal == Signal.SELL  # Score = -1.0, below sell_threshold (-0.5)

    def test_generate_signal_returns_hold_when_score_in_neutral_zone(self, strategy: PrecisionTrendStrategy):
        # Given - Mixed signals that average to neutral
        rule_results = {
            'crossover': Signal.BUY,
            'rsi_threshold': Signal.SELL,
            'adx_threshold': Signal.HOLD,
            'atr_threshold': Signal.HOLD
        }

        # When
        signal = strategy._generate_signal(rule_results)

        # Then
        assert signal == Signal.HOLD  # Score = 0.0, between thresholds

    def test_generate_signal_with_weighted_scoring(self):
        # Given - Strategy with unequal weights
        config = PrecisionTrendStrategyConfig(
            short_ema=5, long_ema=10, rsi_window=14, rsi_oversold=30, rsi_overbought=70,
            adx_window=14, adx_threshold=25, atr_window=14, atr_threshold=0.01,
            weight_crossover=4.0,  # Higher weight
            weight_rsi=1.0,
            weight_adx=1.0,
            weight_atr=1.0,
            buy_threshold=0.5,
            sell_threshold=-0.5
        )
        strategy = PrecisionTrendStrategy(config)

        # Crossover is BUY (weighted heavily), others are SELL
        rule_results = {
            'crossover': Signal.BUY,
            'rsi_threshold': Signal.SELL,
            'adx_threshold': Signal.SELL,
            'atr_threshold': Signal.SELL
        }

        # When
        signal = strategy._generate_signal(rule_results)

        # Then
        # Score = (4/7 * 1) + (1/7 * -1) + (1/7 * -1) + (1/7 * -1) = 1/7 ≈ 0.14
        assert signal == Signal.HOLD  # Score below buy_threshold

    def test_generate_signals_returns_correct_series(self, strategy: PrecisionTrendStrategy):
        # Given
        results = pd.DataFrame({
            'crossover': [Signal.BUY, Signal.BUY, Signal.SELL, Signal.HOLD],
            'rsi_threshold': [Signal.BUY, Signal.HOLD, Signal.SELL, Signal.HOLD],
            'adx_threshold': [Signal.BUY, Signal.BUY, Signal.SELL, Signal.BUY],
            'atr_threshold': [Signal.BUY, Signal.BUY, Signal.SELL, Signal.BUY]
        })

        # When
        signals = strategy._generate_signals(results)

        # Then
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(results)
        # Row 0: All BUY -> score = 1.0 -> BUY
        assert str(signals.iloc[0]) == str(Signal.BUY)
        # Row 2: All SELL -> score = -1.0 -> SELL
        assert str(signals.iloc[2]) == str(Signal.SELL)

    def test_vectorised_compute_with_simple_data(self):
        # Given
        config = PrecisionTrendStrategyConfig(
            short_ema=3, long_ema=5, rsi_window=5, rsi_oversold=30, rsi_overbought=70,
            adx_window=5, adx_threshold=25, atr_window=5, atr_threshold=0.01,
            weight_crossover=1.0, weight_rsi=1.0, weight_adx=1.0, weight_atr=1.0,
            buy_threshold=0.5, sell_threshold=-0.5
        )
        strategy = PrecisionTrendStrategy(config)

        np.random.seed(42)
        n = 50
        ohlc = pd.DataFrame({
            'close': np.linspace(100, 120, n),
            'high': np.linspace(101, 121, n),
            'low': np.linspace(99, 119, n)
        })

        # When
        result = strategy.vectorised_compute(ohlc)

        # Then
        assert 'price' in result.columns
        assert 'short_ema' in result.columns
        assert 'long_ema' in result.columns
        assert 'rsi' in result.columns
        assert 'adx' in result.columns
        assert 'atr' in result.columns
        assert 'signal' in result.columns
        assert len(result) == len(ohlc)

        # Verify all signals are valid (convert to string for comparison due to numpy dtype issues)
        unique_signals = set(str(s) for s in result['signal'].unique())
        valid_signals = {str(Signal.BUY), str(Signal.HOLD), str(Signal.SELL)}
        assert unique_signals.issubset(
            valid_signals), f'Invalid signals: {unique_signals - valid_signals}'

    def test_generate_signal_with_mocked_rules(self):
        # Given
        config = PrecisionTrendStrategyConfig(
            short_ema=5, long_ema=10, rsi_window=14, rsi_oversold=30, rsi_overbought=70,
            adx_window=14, adx_threshold=25, atr_window=14, atr_threshold=0.01,
            weight_crossover=1.0, weight_rsi=1.0, weight_adx=1.0, weight_atr=1.0,
            buy_threshold=0.5, sell_threshold=-0.5
        )
        strategy = PrecisionTrendStrategy(config)

        # Mock all indicators
        for indicator_name in ['short_ema', 'long_ema', 'rsi', 'adx', 'atr']:
            mock_indicator = Mock()
            mock_indicator.update.return_value = 50.0
            strategy.indicators[indicator_name] = mock_indicator

        # Mock all rules to return BUY
        for rule_name in ['crossover', 'rsi_threshold', 'adx_threshold', 'atr_threshold']:
            mock_rule = Mock()
            mock_rule.check.return_value = Signal.BUY
            strategy.rules[rule_name] = mock_rule

        ohlc = pd.Series({'close': 100.0, 'high': 101.0, 'low': 99.0})

        # When
        result = strategy.generate_signal(ohlc)

        # Then
        assert result['signal'] == Signal.BUY
