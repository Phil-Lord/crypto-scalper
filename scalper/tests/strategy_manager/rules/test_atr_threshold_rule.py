import numpy as np
import pandas as pd

from strategy_manager.rules.atr_threshold_rule import AtrThresholdRule


def test_atr_threshold_rule_check_buy():
    rule = AtrThresholdRule(atr_name='atr', threshold=0.002)
    state = {'atr': 0.003}
    assert rule.check(state) == 'buy'


def test_atr_threshold_rule_check_hold():
    rule = AtrThresholdRule(atr_name='atr', threshold=0.002)
    state = {'atr': 0.001}
    assert rule.check(state) == 'hold'


def test_atr_threshold_rule_check_none():
    rule = AtrThresholdRule(atr_name='atr', threshold=0.002)
    state = {'atr': None}
    assert rule.check(state) == 'hold'


def test_atr_threshold_rule_vectorised():
    rule = AtrThresholdRule(atr_name='atr', threshold=0.002)

    df = pd.DataFrame({
        'atr': [0.001, 0.0025, 0.0005, 0.003]
    }, index=pd.date_range("2024-01-01", periods=4, freq="min"))

    result = rule.compute_vectorised(df)

    expected = np.array(['hold', 'buy', 'hold', 'buy'])
    np.testing.assert_array_equal(result, expected)
