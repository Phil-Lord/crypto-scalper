import click
import matplotlib.pyplot as plt
import pandas as pd

from data_system import TradesRepository
from utils import get_second_timestamp, Pair, parse_datetime


@click.command()
@click.option('--pair', required=True, help='Trading pair (e.g. BTC)')
@click.option('--start', required=True, help='Start timestamp (e.g. 2025-1-1-0-0-0)')
@click.option('--end', required=True, help='End timestamp (e.g. 2025-1-1-23-59-59)')
def fetch_trades(pair: str, start: str, end: str) -> None:
    repository = TradesRepository()

    kraken_pair = Pair[pair].value
    start_timestamp = get_second_timestamp(*parse_datetime(start))
    end_timestamp = get_second_timestamp(*parse_datetime(end))

    trades = repository.get(kraken_pair, start_timestamp, end_timestamp)

    trades["timestamp"] = pd.to_datetime(trades["timestamp"], unit="s")

    plt.figure(figsize=(10, 5))
    plt.plot(
        trades['timestamp'],
        trades['price'],
        label='Trade Price',
        color='blue'
    )
    plt.xlabel('Time')
    plt.ylabel('Price')
    plt.title("ETH/USD Trade Prices Over Time")
    plt.legend()
    plt.grid()
    plt.show()


if __name__ == '__main__':
    fetch_trades()
