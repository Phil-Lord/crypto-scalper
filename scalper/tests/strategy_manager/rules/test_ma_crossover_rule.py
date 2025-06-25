import pandas as pd
from strategy_manager.rules import MaCrossoverRule


def test_check_triggers_buy_on_crossover():
    rule = MaCrossoverRule('short', 'long')
    current_state = {
        'short': 105,
        'long': 100,
        'prev_short': 99,
        'prev_long': 100,
        'last_action': 'sell'
    }
    assert rule.check(current_state) == 'buy'


def test_check_triggers_sell_on_crossunder():
    rule = MaCrossoverRule('short', 'long')
    current_state = {
        'short': 95,
        'long': 100,
        'prev_short': 101,
        'prev_long': 100,
        'last_action': 'buy'
    }
    assert rule.check(current_state) == 'sell'


def test_check_returns_hold_if_no_crossover():
    rule = MaCrossoverRule('short', 'long')
    current_state = {
        'short': 101,
        'long': 100,
        'prev_short': 102,
        'prev_long': 99,
        'last_action': 'sell'
    }
    assert rule.check(current_state) == 'hold'


def test_check_returns_hold_if_missing_data():
    rule = MaCrossoverRule('short', 'long')
    current_state = {
        'short': 101,
        'long': 100,
        'prev_short': None,
        'prev_long': 99,
        'last_action': 'sell'
    }
    assert rule.check(current_state) == 'hold'


def test_compute_vectorised_detects_buy_sell():
    rule = MaCrossoverRule('short', 'long')
    df = pd.DataFrame({
        'short': [90, 95, 105, 104, 95, 94],
        'long':  [100, 100, 100, 100, 95, 96],
    })

    signals = rule.compute_vectorised(df)

    # Expect a buy at index 2 and a sell at index 5
    expected = ['hold', 'hold', 'buy', 'hold', 'hold', 'sell']
    assert list(signals) == expected


def test_compute_vectorised_handles_no_crosses():
    rule = MaCrossoverRule('short', 'long')
    df = pd.DataFrame({
        'short': [90, 91, 92, 93, 94, 95],
        'long':  [100, 101, 102, 103, 104, 105],
    })

    signals = rule.compute_vectorised(df)
    assert all(signal == 'hold' for signal in signals)


def test_compute_vectorised_buy_then_hold():
    rule = MaCrossoverRule('short', 'long')
    df = pd.DataFrame({
        'short': [90, 95, 105, 106],
        'long':  [100, 100, 100, 100],
    })

    signals = rule.compute_vectorised(df)
    expected = ['hold', 'hold', 'buy', 'hold']
    assert list(signals) == expected
