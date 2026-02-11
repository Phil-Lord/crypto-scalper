import pandas as pd
import pytest

from strategy_manager.rules.rsi_threshold_rule import RsiThresholdRule


@pytest.mark.strategy_manager
@pytest.mark.rules
@pytest.mark.rsi_threshold_rule
class TestRsiThresholdRule:
    def test_check_triggers_buy_on_cross_above_oversold(self):
        # Given
        rule = RsiThresholdRule(rsi_name='rsi', oversold=30, overbought=70)
        state = {
            'rsi': 35,
            'prev_rsi': 25,
            'last_action': 'sell'
        }

        # When / Then
        assert rule.check(state) == 'buy'

    def test_check_triggers_sell_on_cross_below_overbought(self):
        # Given
        rule = RsiThresholdRule(rsi_name='rsi', oversold=30, overbought=70)
        state = {
            'rsi': 65,
            'prev_rsi': 75,
            'last_action': 'buy'
        }

        # When / Then
        assert rule.check(state) == 'sell'

    def test_check_returns_hold_when_no_cross(self):
        # Given
        rule = RsiThresholdRule(rsi_name='rsi', oversold=30, overbought=70)
        state = {
            'rsi': 65,
            'prev_rsi': 65,
            'last_action': 'buy'
        }

        # When / Then
        assert rule.check(state) == 'hold'

    def test_check_returns_hold_on_missing_data(self):
        # Given
        rule = RsiThresholdRule(rsi_name='rsi', oversold=30, overbought=70)
        state = {
            'rsi': 65,
            'prev_rsi': None,
            'last_action': 'buy'
        }

        # When / Then
        assert rule.check(state) == 'hold'

    def test_compute_vectorised_triggers_buy_and_sell(self):
        # Given
        rule = RsiThresholdRule(rsi_name='rsi', oversold=30, overbought=70)
        df = pd.DataFrame({
            'rsi': [25, 35, 65, 75, 65, 55]
        })

        # When
        signals = rule.compute_vectorised(df)

        # Then
        expected = ['hold', 'buy', 'hold', 'hold', 'sell', 'hold']
        assert list(signals) == expected

    def test_compute_vectorised_handles_no_crosses(self):
        # Given
        rule = RsiThresholdRule(rsi_name='rsi', oversold=30, overbought=70)
        df = pd.DataFrame({
            'rsi': [40, 45, 50, 55, 60]
        })

        # When
        signals = rule.compute_vectorised(df)

        # Then
        assert all(signal == 'hold' for signal in signals)

    def test_compute_vectorised_multiple_buy_sell_cycles(self):
        # Given
        rule = RsiThresholdRule(rsi_name='rsi', oversold=30, overbought=70)
        df = pd.DataFrame({
            'rsi': [25, 35, 75, 65, 25, 35, 75, 65]
        })

        # When
        signals = rule.compute_vectorised(df)

        # Then
        expected = ['hold', 'buy', 'hold', 'sell', 'hold', 'buy', 'hold', 'sell']
        assert list(signals) == expected
