import pandas as pd

from backtesting_engine.profit_calculation import calculate_position_profits, get_final_quote_balance


def test_calculate_position_profits_buy_and_sell():
    df = pd.DataFrame([
        {'signal': 'buy', 'price': 100},
        {'signal': 'sell', 'price': 110}
    ])
    profits = calculate_position_profits(df)
    assert len(profits) == 1
    assert 'profit' in profits.columns
    assert profits.iloc[0]['profit'] > 0


def test_calculate_position_profits_no_trades():
    df = pd.DataFrame([
        {'signal': 'hold', 'price': 100},
        {'signal': 'hold', 'price': 110}
    ])
    profits = calculate_position_profits(df)
    assert profits.empty


def test_get_final_quote_balance_buy_and_sell():
    df = pd.DataFrame([
        {'signal': 'buy', 'price': 100},
        {'signal': 'sell', 'price': 110}
    ])
    balance = get_final_quote_balance(df)
    assert balance > 1000


def test_get_final_quote_balance_no_trades():
    df = pd.DataFrame([
        {'signal': 'hold', 'price': 100},
        {'signal': 'hold', 'price': 110}
    ])
    balance = get_final_quote_balance(df)
    assert balance == 1000
