import numpy as np
import pandas as pd
import pytest

from strategy_manager.rules.atr_threshold_rule import AtrThresholdRule


@pytest.mark.strategy_manager
@pytest.mark.rules
@pytest.mark.atr_threshold_rule
class TestAtrThresholdRule:
    def test_check_returns_buy_when_above_threshold(self):
        # Given
        rule = AtrThresholdRule(atr_name='atr', threshold=0.002)
        state = {'atr': 0.003}

        # When / Then
        assert rule.check(state) == 'buy'

    def test_check_returns_hold_when_below_threshold(self):
        # Given
        rule = AtrThresholdRule(atr_name='atr', threshold=0.002)
        state = {'atr': 0.001}

        # When / Then
        assert rule.check(state) == 'hold'

    def test_check_returns_hold_when_none(self):
        # Given
        rule = AtrThresholdRule(atr_name='atr', threshold=0.002)
        state = {'atr': None}

        # When / Then
        assert rule.check(state) == 'hold'

    def test_compute_vectorised_logic(self):
        # Given
        rule = AtrThresholdRule(atr_name='atr', threshold=0.002)
        df = pd.DataFrame({
            'atr': [0.001, 0.0025, 0.0005, 0.003]
        }, index=pd.date_range('2024-01-01', periods=4, freq='min'))

        # When
        result = rule.compute_vectorised(df)

        # Then
        expected = np.array(['hold', 'buy', 'hold', 'buy'])
        np.testing.assert_array_equal(result, expected)
