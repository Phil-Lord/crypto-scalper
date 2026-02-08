import pandas as pd
import numpy as np
from strategy_manager.rules.adx_threshold_rule import AdxThresholdRule


def test_check_returns_hold_when_adx_is_none():
    rule = AdxThresholdRule(adx_name='adx', threshold=20)
    state = {'adx': None}
    assert rule.check(state) == 'hold'


def test_check_returns_hold_when_below_threshold():
    rule = AdxThresholdRule(adx_name='adx', threshold=25)
    state = {'adx': 20}
    assert rule.check(state) == 'hold'


def test_check_returns_buy_when_above_threshold():
    rule = AdxThresholdRule(adx_name='adx', threshold=20)
    state = {'adx': 30}
    assert rule.check(state) == 'buy'


def test_check_returns_buy_when_equal_to_threshold():
    rule = AdxThresholdRule(adx_name='adx', threshold=25)
    state = {'adx': 25}
    assert rule.check(state) == 'buy'


def test_vectorised_logic_buy_and_hold():
    rule = AdxThresholdRule(adx_name='adx', threshold=20)
    df = pd.DataFrame({'adx': [10, 15, 21, 19, 22, 20]})
    result = rule.compute_vectorised(df)
    expected = ['hold', 'hold', 'buy', 'hold', 'buy', 'buy']
    assert list(result) == expected


def test_vectorised_handles_nans():
    rule = AdxThresholdRule(adx_name='adx', threshold=20)
    df = pd.DataFrame({'adx': [np.nan, 25, np.nan, 19, 21]})
    result = rule.compute_vectorised(df)
    expected = ['hold', 'buy', 'hold', 'hold', 'buy']
    assert list(result) == expected
