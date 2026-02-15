import numpy as np
import pandas as pd
import pytest
from unittest.mock import Mock

from data_system.models.bot_tick_model import Signal
from strategy_manager.strategies.sma_strategy import SmaStrategy
from strategy_manager.strategies.sma_strategy_config import SmaStrategyConfig


@pytest.mark.strategy_manager
@pytest.mark.strategies
@pytest.mark.sma_strategy
class TestSmaStrategy:
    @pytest.fixture
    def strategy(self) -> SmaStrategy:
        config = SmaStrategyConfig(short_window=5, long_window=10)
        return SmaStrategy(config)

    @pytest.fixture
    def sample_ohlc(self) -> pd.Series:
        return pd.Series({'price': 100.0})

    def test_initialisation_registers_indicators_and_rules(self, strategy: SmaStrategy):
        assert 'short_sma' in strategy.indicators
        assert 'long_sma' in strategy.indicators
        assert 'crossover' in strategy.rules

    def test_generate_signal_returns_buy_when_crossover_is_buy(self, strategy: SmaStrategy):
        # Given
        rule_results = {'crossover': Signal.BUY}

        # When
        signal = strategy._generate_signal(rule_results)

        # Then
        assert signal == Signal.BUY

    def test_generate_signal_returns_sell_when_crossover_is_sell(self, strategy: SmaStrategy):
        # Given
        rule_results = {'crossover': Signal.SELL}

        # When
        signal = strategy._generate_signal(rule_results)

        # Then
        assert signal == Signal.SELL

    def test_generate_signal_returns_hold_when_crossover_is_hold(self, strategy: SmaStrategy):
        # Given
        rule_results = {'crossover': Signal.HOLD}

        # When
        signal = strategy._generate_signal(rule_results)

        # Then
        assert signal == Signal.HOLD

    def test_generate_signals_returns_correct_series(self, strategy: SmaStrategy):
        # Given
        results = pd.DataFrame({
            'crossover': [Signal.BUY, Signal.HOLD, Signal.SELL, Signal.HOLD]
        })

        # When
        signals = strategy._generate_signals(results)

        # Then
        assert isinstance(signals, pd.Series)
        assert len(signals) == 4
        assert list(signals) == [Signal.BUY, Signal.HOLD, Signal.SELL, Signal.HOLD]

    def test_generate_signal_with_mocked_indicators(self):
        # Given
        config = SmaStrategyConfig(short_window=5, long_window=10)
        strategy = SmaStrategy(config)

        # Mock the indicators to control their output
        mock_short_sma = Mock()
        mock_short_sma.update.return_value = 105.0
        mock_long_sma = Mock()
        mock_long_sma.update.return_value = 100.0

        strategy.indicators['short_sma'] = mock_short_sma
        strategy.indicators['long_sma'] = mock_long_sma

        # Mock the rule to control crossover detection
        mock_crossover_rule = Mock()
        mock_crossover_rule.check.return_value = Signal.BUY

        strategy.rules['crossover'] = mock_crossover_rule

        ohlc = pd.Series({'price': 105.0})

        # When
        result = strategy.generate_signal(ohlc)

        # Then
        assert result['signal'] == Signal.BUY
        mock_short_sma.update.assert_called_once()
        mock_long_sma.update.assert_called_once()
        mock_crossover_rule.check.assert_called_once()

    def test_generate_signal_suppresses_consecutive_buy_signals(self):
        # Given
        config = SmaStrategyConfig(short_window=5, long_window=10)
        strategy = SmaStrategy(config)

        mock_short_sma = Mock()
        mock_short_sma.update.return_value = 105.0
        mock_long_sma = Mock()
        mock_long_sma.update.return_value = 100.0

        strategy.indicators['short_sma'] = mock_short_sma
        strategy.indicators['long_sma'] = mock_long_sma

        mock_crossover_rule = Mock()
        mock_crossover_rule.check.return_value = Signal.BUY

        strategy.rules['crossover'] = mock_crossover_rule

        ohlc = pd.Series({'price': 105.0})

        # When - Generate first buy signal
        result1 = strategy.generate_signal(ohlc)
        # Generate second buy signal (should be suppressed)
        result2 = strategy.generate_signal(ohlc)

        # Then
        assert result1['signal'] == Signal.BUY
        assert result2['signal'] == Signal.HOLD  # Consecutive buy suppressed

    def test_vectorised_compute_with_simple_data(self):
        # Given
        config = SmaStrategyConfig(short_window=3, long_window=5)
        strategy = SmaStrategy(config)

        # Create simple trending data
        np.random.seed(42)
        prices = np.linspace(100, 120, 20)
        ohlc = pd.DataFrame({'price': prices})

        # When
        result = strategy.vectorised_compute(ohlc)

        # Then
        assert 'price' in result.columns
        assert 'short_sma' in result.columns
        assert 'long_sma' in result.columns
        assert 'crossover' in result.columns
        assert 'signal' in result.columns
        assert len(result) == len(ohlc)
        # Signals should only be BUY, HOLD, or SELL
        assert result['signal'].isin([Signal.BUY, Signal.HOLD, Signal.SELL]).all()
