import pytest

from strategy_manager.strategy_manager import StrategyManager
from strategy_manager.strategies.sma_strategy import SmaStrategy
from strategy_manager.strategies.precision_trend_strategy import PrecisionTrendStrategy


@pytest.mark.strategy_manager
@pytest.mark.strategy_manager_class
class TestStrategyManager:
    @pytest.fixture
    def manager(self) -> StrategyManager:
        '''Create a StrategyManager instance.'''
        return StrategyManager()

    def test_initialisation_registers_strategies(self, manager: StrategyManager):
        # Given / When / Then
        assert 'SmaStrategy' in manager.strategies
        assert 'PrecisionTrendStrategy' in manager.strategies

    def test_get_strategy_returns_sma_strategy(self, manager: StrategyManager):
        # Given
        strategy_name = 'SmaStrategy'
        kwargs = {'short_window': 5, 'long_window': 10}

        # When
        strategy = manager.get_strategy(strategy_name, **kwargs)

        # Then
        assert isinstance(strategy, SmaStrategy)
        assert 'short_sma' in strategy.indicators
        assert 'long_sma' in strategy.indicators

    def test_get_strategy_returns_precision_trend_strategy(self, manager: StrategyManager):
        # Given
        strategy_name = 'PrecisionTrendStrategy'
        kwargs = {
            'short_ema': 5,
            'long_ema': 10,
            'rsi_window': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'adx_window': 14,
            'adx_threshold': 25,
            'atr_window': 14,
            'atr_threshold': 0.01,
            'weight_crossover': 1.0,
            'weight_rsi': 1.0,
            'weight_adx': 1.0,
            'weight_atr': 1.0,
            'buy_threshold': 0.5,
            'sell_threshold': -0.5
        }

        # When
        strategy = manager.get_strategy(strategy_name, **kwargs)

        # Then
        assert isinstance(strategy, PrecisionTrendStrategy)
        assert 'short_ema' in strategy.indicators
        assert 'rsi' in strategy.indicators

    def test_get_strategy_raises_error_for_unknown_strategy(self, manager: StrategyManager):
        # Given
        strategy_name = 'UnknownStrategy'

        # When / Then
        with pytest.raises(ValueError, match='Strategy UnknownStrategy does not exist'):
            manager.get_strategy(strategy_name)

    def test_get_strategy_passes_kwargs_to_strategy(self, manager: StrategyManager):
        # Given
        strategy_name = 'SmaStrategy'
        short_window = 7
        long_window = 21

        # When
        strategy = manager.get_strategy(
            strategy_name,
            short_window=short_window,
            long_window=long_window
        )

        # Then
        assert isinstance(strategy, SmaStrategy)
        assert strategy.indicators['short_sma'].window == short_window
        assert strategy.indicators['long_sma'].window == long_window
