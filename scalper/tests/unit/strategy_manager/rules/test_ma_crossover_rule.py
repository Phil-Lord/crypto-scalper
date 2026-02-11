import pandas as pd
import pytest

from strategy_manager.rules.ma_crossover_rule import MaCrossoverRule


@pytest.mark.strategy_manager
@pytest.mark.rules
@pytest.mark.ma_crossover_rule
class TestMaCrossoverRule:
    def test_check_triggers_buy_on_crossover(self):
        # Given
        rule = MaCrossoverRule('short', 'long')
        current_state = {
            'short': 105,
            'long': 100,
            'prev_short': 99,
            'prev_long': 100,
            'last_action': 'sell'
        }

        # When / Then
        assert rule.check(current_state) == 'buy'

    def test_check_triggers_sell_on_crossunder(self):
        # Given
        rule = MaCrossoverRule('short', 'long')
        current_state = {
            'short': 95,
            'long': 100,
            'prev_short': 101,
            'prev_long': 100,
            'last_action': 'buy'
        }

        # When / Then
        assert rule.check(current_state) == 'sell'

    def test_check_returns_hold_when_no_crossover(self):
        # Given
        rule = MaCrossoverRule('short', 'long')
        current_state = {
            'short': 101,
            'long': 100,
            'prev_short': 102,
            'prev_long': 99,
            'last_action': 'sell'
        }

        # When / Then
        assert rule.check(current_state) == 'hold'

    def test_check_returns_hold_when_missing_data(self):
        # Given
        rule = MaCrossoverRule('short', 'long')
        current_state = {
            'short': 101,
            'long': 100,
            'prev_short': None,
            'prev_long': 99,
            'last_action': 'sell'
        }

        # When / Then
        assert rule.check(current_state) == 'hold'

    def test_compute_vectorised_detects_buy_sell(self):
        # Given
        rule = MaCrossoverRule('short', 'long')
        df = pd.DataFrame({
            'short': [90, 95, 105, 104, 95, 94],
            'long':  [100, 100, 100, 100, 95, 96],
        })

        # When
        signals = rule.compute_vectorised(df)

        # Then
        expected = ['hold', 'hold', 'buy', 'hold', 'hold', 'sell']
        assert list(signals) == expected

    def test_compute_vectorised_handles_no_crosses(self):
        # Given
        rule = MaCrossoverRule('short', 'long')
        df = pd.DataFrame({
            'short': [90, 91, 92, 93, 94, 95],
            'long':  [100, 101, 102, 103, 104, 105],
        })

        # When
        signals = rule.compute_vectorised(df)

        # Then
        assert all(signal == 'hold' for signal in signals)

    def test_compute_vectorised_buy_then_hold(self):
        # Given
        rule = MaCrossoverRule('short', 'long')
        df = pd.DataFrame({
            'short': [90, 95, 105, 106],
            'long':  [100, 100, 100, 100],
        })

        # When
        signals = rule.compute_vectorised(df)

        # Then
        expected = ['hold', 'hold', 'buy', 'hold']
        assert list(signals) == expected
