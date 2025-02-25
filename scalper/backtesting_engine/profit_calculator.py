import numpy as np
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


def simulate_state_transitions(results: pd.DataFrame) -> pd.DataFrame:
    df = results.copy()

    # Create boolean masks for buy/sell signals.
    buy_signals = (df['signal'] == 'buy')
    sell_signals = (df['signal'] == 'sell')

    # Convert to numeric state changes (+1 buy, -1 sell) to calculate cumulative position state.
    state_changes = buy_signals.astype(int) - sell_signals.astype(int)
    cumulative_state = state_changes.cumsum().clip(lower=0, upper=1)

    # Map numeric states to position labels.
    df['position'] = np.where(cumulative_state, 'long', 'out')
    return df
