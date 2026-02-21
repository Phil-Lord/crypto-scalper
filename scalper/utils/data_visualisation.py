import logging

import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)


def plot_position_profits(position_profits: pd.DataFrame) -> None:
    if position_profits.empty:
        logger.warning('No positions to plot.')
        return

    plt.figure(figsize=(10, 5))
    plt.bar(position_profits.index, position_profits['profit'], color=[
            'green' if p >= 0 else 'red' for p in position_profits['profit']])
    plt.axhline(0, color='black', linewidth=1)
    plt.xlabel('Trade Index')
    plt.ylabel('Profit per Position (Quote Currency)')
    plt.title('Profit per Position')
    plt.show()


def plot_results(results: pd.DataFrame, pair: str) -> None:
    # Extract buys and sells.
    buys = results[results['signal'] == 'buy']
    sells = results[results['signal'] == 'sell']

    plt.figure(figsize=(12, 6))

    # Plot price.
    plt.plot(results.index, results['price'], label='Price', color='blue', alpha=0.4)

    # Plot SMAs.
    if 'short_sma' in results.columns:
        plot_line(results, 'short_sma', 'purple')
    if 'long_sma' in results.columns:
        plot_line(results, 'long_sma', 'green')
    if 'short_ema' in results.columns:
        plot_line(results, 'short_ema', 'orange')
    if 'long_ema' in results.columns:
        plot_line(results, 'long_ema', 'yellow')

    # Plot buys and sells.
    plt.scatter(buys.index, buys['price'], color='green',
                label='Buy Signal', marker='^', alpha=1, s=100)
    plt.scatter(sells.index, sells['price'], color='red',
                label='Sell Signal', marker='v', alpha=1, s=100)

    # Titles, legends, etc.
    plt.title(f'Price Movement for {pair}')
    plt.xlabel('Time')
    plt.ylabel('Price')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.show()


def plot_line(results: pd.DataFrame, column_name: str, colour: str) -> None:
    plt.plot(results.index, results[column_name], label=column_name, color=colour, linestyle='--')


def plot_trade_data_from_db(trades: list) -> None:
    '''
    Plot trade prices over time.

    :param trades: List of objects with .timestamp, .price, .volume, .side attributes.
    '''
    if not trades:
        logger.warning('No trades to plot.')
        return

    trades_df = pd.DataFrame([
        {
            'timestamp': t.timestamp,
            'price': t.price,
            'volume': t.volume,
            'side': t.side
        }
        for t in trades
    ])
    trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'], unit='s')

    plt.figure(figsize=(10, 5))
    plt.plot(
        trades_df['timestamp'],
        trades_df['price'],
        label='Trade Price',
        color='blue'
    )
    plt.xlabel('Time')
    plt.ylabel('Price')
    plt.title('Trade Prices Over Time')
    plt.legend()
    plt.grid()
    plt.show()
