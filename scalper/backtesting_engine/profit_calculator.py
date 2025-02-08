import pandas as pd


def calculate_position_profits(results: pd.DataFrame, initial_quote_balance: float = 1000) -> pd.DataFrame:
    positions = []
    quote_balance = initial_quote_balance
    base_balance = 0
    entry_price = None
    entry_time = None

    for index, row in results.iterrows():
        signal, price = row['signal'], row['price']

        if signal == 'buy' and quote_balance > 0:
            base_balance = quote_balance / price
            entry_price = price
            entry_time = index
            quote_balance = 0
        elif signal == 'sell' and base_balance > 0:
            profit = (price - entry_price) * base_balance
            positions.append({'entry_time': entry_time, 'exit_time': index, 'profit': profit})
            quote_balance = base_balance * price
            base_balance = 0

    if base_balance > 0:
        quote_balance = base_balance * results.iloc[-1]['price']
    print(quote_balance)

    return pd.DataFrame(positions)
