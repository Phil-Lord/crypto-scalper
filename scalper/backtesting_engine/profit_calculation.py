import pandas as pd


def calculate_position_profits(results: pd.DataFrame, initial_quote_balance: float = 1000) -> pd.DataFrame:
    '''
    Calculate profit for each completed position (buy → sell cycle).

    Applies 0.04% trading fee on both buy and sell sides.

    :param results: DataFrame with 'signal' and 'price' columns, indexed by timestamp.
    :param initial_quote_balance: Starting balance in quote currency (default: 1000).
    :return: DataFrame with columns 'entry_time', 'exit_time', 'profit'.
    '''
    positions = []
    quote_balance = initial_quote_balance
    base_balance = 0.0
    entry_price = None
    entry_time = None
    fee = 0.0004

    for row in results.itertuples():
        signal, price, index = row.signal, row.price, row.Index

        if signal == 'buy' and quote_balance > 0:
            base_balance = (quote_balance / price) * (1 - fee)
            entry_price = price
            entry_time = index
            quote_balance = 0.0
        elif signal == 'sell' and base_balance > 0:
            gross_sell = base_balance * price
            net_sell = gross_sell * (1 - fee)
            profit = net_sell - (entry_price * base_balance)
            positions.append({'entry_time': entry_time, 'exit_time': index, 'profit': profit})
            quote_balance = net_sell
            base_balance = 0.0

    return pd.DataFrame(positions)


def get_final_quote_balance(results: pd.DataFrame, initial_quote_balance: float = 1000) -> float:
    '''
    Calculate final quote balance after executing all signals.

    If still holding a position at the end, values it at the final market price.
    Applies 0.04% trading fee on both buy and sell sides.

    :param results: DataFrame with 'signal' and 'price' columns, indexed by timestamp.
    :param initial_quote_balance: Starting balance in quote currency (default: 1000).
    :return: Final balance in quote currency.
    '''
    quote_balance = initial_quote_balance
    base_balance = 0.0
    fee = 0.0004

    for row in results.itertuples():
        if row.signal == 'buy' and quote_balance > 0:
            base_balance = (quote_balance / row.price) * (1 - fee)
            quote_balance = 0.0
        elif row.signal == 'sell' and base_balance > 0:
            quote_balance = base_balance * row.price * (1 - fee)
            base_balance = 0.0

    if base_balance > 0:
        quote_balance += base_balance * results.iloc[-1].price * (1 - fee)

    return quote_balance
