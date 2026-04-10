import pandas as pd
import pytest
from unittest.mock import Mock

from data_system.models.bot_tick_model import Signal
from strategy_manager.strategies.base_strategy import Strategy


class ConcreteStrategy(Strategy):
    '''Minimal concrete implementation of Strategy for testing base class behaviour.'''

    @property
    def warmup_candles(self) -> int:
        return 0

    def _generate_signal(self, rule_results: dict) -> Signal:
        return rule_results.get('test_rule', Signal.HOLD)

    def _generate_signals(self, results: pd.DataFrame) -> pd.Series:
        return results['test_rule']


def make_mock_indicator(return_value: float = 1.0) -> Mock:
    indicator = Mock()
    indicator.update.return_value = return_value
    indicator.compute_vectorised.return_value = pd.Series([return_value])
    return indicator


def make_mock_rule(return_value: Signal = Signal.HOLD) -> Mock:
    rule = Mock()
    rule.check.return_value = return_value
    rule.compute_vectorised.return_value = pd.Series([return_value])
    return rule


@pytest.mark.strategy_manager
@pytest.mark.strategies
@pytest.mark.base_strategy
class TestStrategyRegister:
    def test_register_indicator_adds_to_indicators_dict(self):
        strategy = ConcreteStrategy()
        indicator = make_mock_indicator()
        strategy.register_indicator('my_indicator', indicator)
        assert strategy.indicators['my_indicator'] is indicator

    def test_register_rule_adds_to_rules_dict(self):
        strategy = ConcreteStrategy()
        rule = make_mock_rule()
        strategy.register_rule('my_rule', rule)
        assert strategy.rules['my_rule'] is rule

    def test_register_multiple_indicators(self):
        strategy = ConcreteStrategy()
        ind_a = make_mock_indicator(1.0)
        ind_b = make_mock_indicator(2.0)
        strategy.register_indicator('a', ind_a)
        strategy.register_indicator('b', ind_b)
        assert strategy.indicators['a'] is ind_a
        assert strategy.indicators['b'] is ind_b

    def test_register_indicator_with_same_name_overwrites_existing(self):
        strategy = ConcreteStrategy()
        original = make_mock_indicator(1.0)
        replacement = make_mock_indicator(2.0)
        strategy.register_indicator('ind', original)
        strategy.register_indicator('ind', replacement)
        assert strategy.indicators['ind'] is replacement


@pytest.mark.strategy_manager
@pytest.mark.strategies
@pytest.mark.base_strategy
class TestGenerateSignal:
    @pytest.fixture
    def strategy(self) -> ConcreteStrategy:
        s = ConcreteStrategy()
        s.register_indicator('ind', make_mock_indicator(42.0))
        s.register_rule('test_rule', make_mock_rule(Signal.HOLD))
        return s

    def test_returns_dict_with_expected_keys(self, strategy: ConcreteStrategy):
        ohlc = pd.Series({'close': 100.0})
        result = strategy.generate_signal(ohlc)
        assert 'price' in result
        assert 'ind' in result
        assert 'test_rule' in result
        assert 'signal' in result

    def test_price_is_close_value(self, strategy: ConcreteStrategy):
        ohlc = pd.Series({'close': 99.5})
        result = strategy.generate_signal(ohlc)
        assert result['price'] == 99.5

    def test_calls_indicator_update_with_ohlc(self, strategy: ConcreteStrategy):
        ohlc = pd.Series({'close': 100.0})
        strategy.generate_signal(ohlc)
        strategy.indicators['ind'].update.assert_called_once_with(ohlc)

    def test_calls_rule_check_with_current_state(self, strategy: ConcreteStrategy):
        ohlc = pd.Series({'close': 100.0})
        strategy.generate_signal(ohlc)
        call_args = strategy.rules['test_rule'].check.call_args[0][0]
        assert 'ind' in call_args
        assert 'last_action' in call_args

    def test_current_state_includes_last_action(self, strategy: ConcreteStrategy):
        ohlc = pd.Series({'close': 100.0})
        strategy.generate_signal(ohlc)
        call_args = strategy.rules['test_rule'].check.call_args[0][0]
        assert call_args['last_action'] == Signal.SELL  # Initial last_action

    def test_prev_indicator_values_included_on_second_call(self, strategy: ConcreteStrategy):
        ohlc = pd.Series({'close': 100.0})
        strategy.generate_signal(ohlc)
        strategy.generate_signal(ohlc)
        call_args = strategy.rules['test_rule'].check.call_args[0][0]
        assert 'prev_ind' in call_args
        assert call_args['prev_ind'] == 42.0

    def test_prev_indicator_values_not_present_on_first_call(self, strategy: ConcreteStrategy):
        ohlc = pd.Series({'close': 100.0})
        strategy.generate_signal(ohlc)
        call_args = strategy.rules['test_rule'].check.call_args[0][0]
        assert 'prev_ind' not in call_args

    def test_initial_sell_is_suppressed_to_hold(self):
        # last_action starts as SELL so a SELL signal on the first call is suppressed
        strategy = ConcreteStrategy()
        strategy.register_indicator('ind', make_mock_indicator())
        strategy.register_rule('test_rule', make_mock_rule(Signal.SELL))
        ohlc = pd.Series({'close': 100.0})
        result = strategy.generate_signal(ohlc)
        assert result['signal'] == Signal.HOLD

    def test_buy_signal_passes_through_initially(self):
        strategy = ConcreteStrategy()
        strategy.register_indicator('ind', make_mock_indicator())
        strategy.register_rule('test_rule', make_mock_rule(Signal.BUY))
        ohlc = pd.Series({'close': 100.0})
        result = strategy.generate_signal(ohlc)
        assert result['signal'] == Signal.BUY

    def test_consecutive_buy_signals_suppresses_second(self):
        strategy = ConcreteStrategy()
        strategy.register_indicator('ind', make_mock_indicator())
        strategy.register_rule('test_rule', make_mock_rule(Signal.BUY))
        ohlc = pd.Series({'close': 100.0})
        first = strategy.generate_signal(ohlc)
        second = strategy.generate_signal(ohlc)
        assert first['signal'] == Signal.BUY
        assert second['signal'] == Signal.HOLD

    def test_consecutive_sell_signals_suppresses_second(self):
        # Given - first establish a BUY action so SELL can pass, then repeat SELL
        strategy = ConcreteStrategy()
        strategy.register_indicator('ind', make_mock_indicator())
        rule = make_mock_rule()
        strategy.register_rule('test_rule', rule)
        ohlc = pd.Series({'close': 100.0})

        rule.check.return_value = Signal.BUY
        strategy.generate_signal(ohlc)  # last_action → BUY

        rule.check.return_value = Signal.SELL
        first_sell = strategy.generate_signal(ohlc)  # SELL passes
        second_sell = strategy.generate_signal(ohlc)  # SELL suppressed

        assert first_sell['signal'] == Signal.SELL
        assert second_sell['signal'] == Signal.HOLD

    def test_alternating_buy_sell_not_suppressed(self):
        strategy = ConcreteStrategy()
        strategy.register_indicator('ind', make_mock_indicator())
        rule = make_mock_rule()
        strategy.register_rule('test_rule', rule)
        ohlc = pd.Series({'close': 100.0})

        rule.check.return_value = Signal.BUY
        buy_result = strategy.generate_signal(ohlc)
        rule.check.return_value = Signal.SELL
        sell_result = strategy.generate_signal(ohlc)

        assert buy_result['signal'] == Signal.BUY
        assert sell_result['signal'] == Signal.SELL

    def test_hold_does_not_update_last_action(self):
        strategy = ConcreteStrategy()
        strategy.register_indicator('ind', make_mock_indicator())
        rule = make_mock_rule()
        strategy.register_rule('test_rule', rule)
        ohlc = pd.Series({'close': 100.0})

        rule.check.return_value = Signal.BUY
        strategy.generate_signal(ohlc)  # last_action → BUY

        rule.check.return_value = Signal.HOLD
        strategy.generate_signal(ohlc)  # HOLD, last_action stays BUY

        rule.check.return_value = Signal.BUY
        third = strategy.generate_signal(ohlc)  # BUY == last_action → suppressed

        assert third['signal'] == Signal.HOLD

    def test_last_action_updated_after_buy(self):
        strategy = ConcreteStrategy()
        strategy.register_indicator('ind', make_mock_indicator())
        strategy.register_rule('test_rule', make_mock_rule(Signal.BUY))
        ohlc = pd.Series({'close': 100.0})
        strategy.generate_signal(ohlc)
        assert strategy.last_action == Signal.BUY

    def test_last_action_updated_after_sell(self):
        strategy = ConcreteStrategy()
        strategy.register_indicator('ind', make_mock_indicator())
        rule = make_mock_rule()
        strategy.register_rule('test_rule', rule)
        ohlc = pd.Series({'close': 100.0})

        rule.check.return_value = Signal.BUY
        strategy.generate_signal(ohlc)  # last_action → BUY

        rule.check.return_value = Signal.SELL
        strategy.generate_signal(ohlc)  # last_action → SELL

        assert strategy.last_action == Signal.SELL

    def test_indicator_result_included_in_return_dict(self, strategy: ConcreteStrategy):
        ohlc = pd.Series({'close': 100.0})
        result = strategy.generate_signal(ohlc)
        assert result['ind'] == 42.0

    def test_no_indicators_or_rules_returns_valid_dict(self):
        strategy = ConcreteStrategy()
        ohlc = pd.Series({'close': 50.0})
        result = strategy.generate_signal(ohlc)
        assert result['price'] == 50.0
        assert 'signal' in result


@pytest.mark.strategy_manager
@pytest.mark.strategies
@pytest.mark.base_strategy
class TestVectorisedCompute:
    def test_returns_dataframe_with_price_column(self):
        strategy = ConcreteStrategy()
        indicator = Mock()
        indicator.compute_vectorised.return_value = pd.Series([1.0, 2.0, 3.0])
        rule = Mock()
        rule.compute_vectorised.return_value = pd.Series(
            [Signal.BUY, Signal.SELL, Signal.BUY])
        strategy.register_indicator('ind', indicator)
        strategy.register_rule('test_rule', rule)

        ohlc = pd.DataFrame({'close': [100.0, 101.0, 102.0]})
        result = strategy.vectorised_compute(ohlc)

        assert 'price' in result.columns
        assert list(result['price']) == [100.0, 101.0, 102.0]

    def test_returns_dataframe_with_indicator_columns(self):
        strategy = ConcreteStrategy()
        indicator = Mock()
        indicator.compute_vectorised.return_value = pd.Series([10.0, 20.0])
        rule = Mock()
        rule.compute_vectorised.return_value = pd.Series([Signal.HOLD, Signal.BUY])
        strategy.register_indicator('my_ind', indicator)
        strategy.register_rule('test_rule', rule)

        ohlc = pd.DataFrame({'close': [100.0, 101.0]})
        result = strategy.vectorised_compute(ohlc)

        assert 'my_ind' in result.columns

    def test_returns_dataframe_with_rule_and_signal_columns(self):
        strategy = ConcreteStrategy()
        indicator = Mock()
        indicator.compute_vectorised.return_value = pd.Series([1.0, 2.0])
        rule = Mock()
        rule.compute_vectorised.return_value = pd.Series([Signal.BUY, Signal.SELL])
        strategy.register_indicator('ind', indicator)
        strategy.register_rule('test_rule', rule)

        ohlc = pd.DataFrame({'close': [100.0, 101.0]})
        result = strategy.vectorised_compute(ohlc)

        assert 'test_rule' in result.columns
        assert 'signal' in result.columns

    def test_calls_compute_vectorised_on_each_indicator(self):
        strategy = ConcreteStrategy()
        ind_a = Mock()
        ind_a.compute_vectorised.return_value = pd.Series([1.0])
        ind_b = Mock()
        ind_b.compute_vectorised.return_value = pd.Series([2.0])
        rule = Mock()
        rule.compute_vectorised.return_value = pd.Series([Signal.HOLD])
        strategy.register_indicator('a', ind_a)
        strategy.register_indicator('b', ind_b)
        strategy.register_rule('test_rule', rule)

        ohlc = pd.DataFrame({'close': [100.0]})
        strategy.vectorised_compute(ohlc)

        ind_a.compute_vectorised.assert_called_once_with(ohlc)
        ind_b.compute_vectorised.assert_called_once_with(ohlc)

    def test_calls_compute_vectorised_on_each_rule(self):
        strategy = ConcreteStrategy()
        indicator = Mock()
        indicator.compute_vectorised.return_value = pd.Series([1.0])
        rule = Mock()
        rule.compute_vectorised.return_value = pd.Series([Signal.HOLD])
        strategy.register_indicator('ind', indicator)
        strategy.register_rule('test_rule', rule)

        ohlc = pd.DataFrame({'close': [100.0]})
        strategy.vectorised_compute(ohlc)

        rule.compute_vectorised.assert_called_once()

    def test_consecutive_signals_suppressed_in_output(self):
        strategy = ConcreteStrategy()
        indicator = Mock()
        indicator.compute_vectorised.return_value = pd.Series([1.0, 1.0, 1.0])
        rule = Mock()
        rule.compute_vectorised.return_value = pd.Series(
            [Signal.BUY, Signal.BUY, Signal.SELL])
        strategy.register_indicator('ind', indicator)
        strategy.register_rule('test_rule', rule)

        ohlc = pd.DataFrame({'close': [100.0, 101.0, 102.0]})
        result = strategy.vectorised_compute(ohlc)

        signals = list(result['signal'])
        assert signals[0] == Signal.BUY
        assert signals[1] == Signal.HOLD   # Consecutive BUY suppressed
        assert signals[2] == Signal.SELL


@pytest.mark.strategy_manager
@pytest.mark.strategies
@pytest.mark.base_strategy
class TestSuppressConsecutiveSignals:
    @pytest.fixture
    def strategy(self) -> ConcreteStrategy:
        return ConcreteStrategy()

    def _suppress(self, strategy: ConcreteStrategy, signals: list[Signal]) -> list[Signal]:
        series = pd.Series(signals)
        return list(strategy._suppress_consecutive_signals(series))

    def test_first_sell_suppressed_because_last_action_starts_as_sell(
            self, strategy: ConcreteStrategy):
        result = self._suppress(strategy, [Signal.SELL])
        assert result == [Signal.HOLD]

    def test_first_buy_passes_through(self, strategy: ConcreteStrategy):
        result = self._suppress(strategy, [Signal.BUY])
        assert result == [Signal.BUY]

    def test_first_hold_passes_through(self, strategy: ConcreteStrategy):
        result = self._suppress(strategy, [Signal.HOLD])
        assert result == [Signal.HOLD]

    def test_consecutive_buys(self, strategy: ConcreteStrategy):
        result = self._suppress(strategy, [Signal.BUY, Signal.BUY])
        assert result == [Signal.BUY, Signal.HOLD]

    def test_consecutive_sells_both_suppressed(self, strategy: ConcreteStrategy):
        # First SELL suppressed (last_action=SELL), second SELL also suppressed
        result = self._suppress(strategy, [Signal.SELL, Signal.SELL])
        assert result == [Signal.HOLD, Signal.HOLD]

    def test_buy_then_sell_alternating_passes_through(self, strategy: ConcreteStrategy):
        result = self._suppress(strategy, [Signal.BUY, Signal.SELL, Signal.BUY, Signal.SELL])
        assert result == [Signal.BUY, Signal.SELL, Signal.BUY, Signal.SELL]

    def test_all_hold_passes_through(self, strategy: ConcreteStrategy):
        result = self._suppress(strategy, [Signal.HOLD, Signal.HOLD, Signal.HOLD])
        assert result == [Signal.HOLD, Signal.HOLD, Signal.HOLD]

    def test_hold_between_same_signals_still_suppresses(self, strategy: ConcreteStrategy):
        # BUY, HOLD, BUY → BUY passes, HOLD passes, second BUY suppressed (last_action still BUY)
        result = self._suppress(strategy, [Signal.BUY, Signal.HOLD, Signal.BUY])
        assert result == [Signal.BUY, Signal.HOLD, Signal.HOLD]

    def test_hold_does_not_reset_last_action(self, strategy: ConcreteStrategy):
        # BUY, HOLD, SELL → all pass (HOLD doesn't change last_action, so SELL != BUY)
        result = self._suppress(strategy, [Signal.BUY, Signal.HOLD, Signal.SELL])
        assert result == [Signal.BUY, Signal.HOLD, Signal.SELL]

    def test_empty_series_returns_empty_series(self, strategy: ConcreteStrategy):
        result = self._suppress(strategy, [])
        assert result == []

    def test_single_buy_returns_buy(self, strategy: ConcreteStrategy):
        result = self._suppress(strategy, [Signal.BUY])
        assert result == [Signal.BUY]

    def test_preserves_series_index(self, strategy: ConcreteStrategy):
        signals = pd.Series(
            [Signal.BUY, Signal.SELL],
            index=[10, 20],
        )
        result = strategy._suppress_consecutive_signals(signals)
        assert list(result.index) == [10, 20]

    def test_long_sequence_with_mixed_signals(self, strategy: ConcreteStrategy):
        signals = [
            Signal.BUY, Signal.BUY, Signal.HOLD, Signal.SELL,
            Signal.SELL, Signal.BUY, Signal.HOLD, Signal.BUY,
        ]
        result = self._suppress(strategy, signals)
        expected = [
            Signal.BUY,   # Passes (last_action=SELL initially)
            Signal.HOLD,  # BUY suppressed
            Signal.HOLD,  # HOLD
            Signal.SELL,  # Passes (last_action=BUY)
            Signal.HOLD,  # SELL suppressed
            Signal.BUY,   # Passes (last_action=SELL)
            Signal.HOLD,  # HOLD
            Signal.HOLD,  # BUY suppressed (last_action still BUY)
        ]
        assert result == expected


@pytest.mark.strategy_manager
@pytest.mark.strategies
@pytest.mark.base_strategy
class TestReset:
    def test_reset_sets_last_action_to_sell(self):
        strategy = ConcreteStrategy()
        strategy.register_indicator('ind', make_mock_indicator())
        strategy.register_rule('test_rule', make_mock_rule(Signal.BUY))
        ohlc = pd.Series({'close': 100.0})
        strategy.generate_signal(ohlc)  # last_action now BUY

        strategy.reset()

        assert strategy.last_action == Signal.SELL

    def test_reset_clears_prev_indicator_values(self):
        strategy = ConcreteStrategy()
        strategy.register_indicator('ind', make_mock_indicator())
        strategy.register_rule('test_rule', make_mock_rule())
        ohlc = pd.Series({'close': 100.0})
        strategy.generate_signal(ohlc)  # Populates prev_indicator_values
        assert strategy.prev_indicator_values != {}

        strategy.reset()

        assert strategy.prev_indicator_values == {}

    def test_reset_calls_reset_on_all_indicators(self):
        strategy = ConcreteStrategy()
        ind_a = make_mock_indicator()
        ind_b = make_mock_indicator()
        strategy.register_indicator('a', ind_a)
        strategy.register_indicator('b', ind_b)

        strategy.reset()

        ind_a.reset.assert_called_once()
        ind_b.reset.assert_called_once()

    def test_reset_does_not_call_reset_on_rules(self):
        # Rules have no state to reset; verify reset() doesn't call rule.reset()
        strategy = ConcreteStrategy()
        rule = make_mock_rule()
        strategy.register_rule('test_rule', rule)

        strategy.reset()

        rule.reset.assert_not_called()

    def test_reset_with_no_indicators_does_not_raise(self):
        strategy = ConcreteStrategy()
        strategy.reset()  # Should not raise
        assert strategy.last_action == Signal.SELL
        assert strategy.prev_indicator_values == {}

    def test_reset_restores_generate_signal_behaviour_to_initial_state(self):
        # Given — run strategy to build up state
        strategy = ConcreteStrategy()
        ind = make_mock_indicator()
        rule = make_mock_rule()
        strategy.register_indicator('ind', ind)
        strategy.register_rule('test_rule', rule)
        ohlc = pd.Series({'close': 100.0})

        rule.check.return_value = Signal.BUY
        strategy.generate_signal(ohlc)  # last_action → BUY, prev_indicator_values populated

        # When
        strategy.reset()
        ind.reset.reset_mock()  # Clear call history from reset()

        # Then — initial SELL signal should be suppressed again (last_action back to SELL)
        rule.check.return_value = Signal.SELL
        result = strategy.generate_signal(ohlc)
        assert result['signal'] == Signal.HOLD  # SELL suppressed because last_action = SELL

    def test_reset_prev_indicator_values_not_leaked_to_next_call(self):
        strategy = ConcreteStrategy()
        ind = make_mock_indicator(99.0)
        rule = make_mock_rule()
        strategy.register_indicator('ind', ind)
        strategy.register_rule('test_rule', rule)
        ohlc = pd.Series({'close': 100.0})

        strategy.generate_signal(ohlc)  # Populates prev_indicator_values
        strategy.reset()
        strategy.generate_signal(ohlc)  # First call after reset

        # prev_ind should NOT be in current_state on the first call after reset
        call_args = rule.check.call_args[0][0]
        assert 'prev_ind' not in call_args
