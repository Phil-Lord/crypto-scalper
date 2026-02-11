import numpy as np
import pandas as pd
import pytest

from strategy_manager.rules.adx_threshold_rule import AdxThresholdRule


@pytest.mark.strategy_manager
@pytest.mark.rules
@pytest.mark.adx_threshold_rule
class TestAdxThresholdRule:
    def test_check_returns_hold_when_adx_is_none(self):
        # Given
        rule = AdxThresholdRule(adx_name='adx', threshold=20)
        state = {'adx': None}

        # When / Then
        assert rule.check(state) == 'hold'

    def test_check_returns_hold_when_below_threshold(self):
        # Given
        rule = AdxThresholdRule(adx_name='adx', threshold=25)
        state = {'adx': 20}

        # When / Then
        assert rule.check(state) == 'hold'

    def test_check_returns_buy_when_above_threshold(self):
        # Given
        rule = AdxThresholdRule(adx_name='adx', threshold=20)
        state = {'adx': 30}

        # When / Then
        assert rule.check(state) == 'buy'

    def test_check_returns_buy_when_equal_to_threshold(self):
        # Given
        rule = AdxThresholdRule(adx_name='adx', threshold=25)
        state = {'adx': 25}

        # When / Then
        assert rule.check(state) == 'buy'

    def test_compute_vectorised_logic_buy_and_hold(self):
        # Given
        rule = AdxThresholdRule(adx_name='adx', threshold=20)
        df = pd.DataFrame({'adx': [10, 15, 21, 19, 22, 20]})

        # When
        result = rule.compute_vectorised(df)

        # Then
        expected = ['hold', 'hold', 'buy', 'hold', 'buy', 'buy']
        assert list(result) == expected

    def test_compute_vectorised_handles_nans(self):
        # Given
        rule = AdxThresholdRule(adx_name='adx', threshold=20)
        df = pd.DataFrame({'adx': [np.nan, 25, np.nan, 19, 21]})

        # When
        result = rule.compute_vectorised(df)

        # Then
        expected = ['hold', 'buy', 'hold', 'hold', 'buy']
        assert list(result) == expected
