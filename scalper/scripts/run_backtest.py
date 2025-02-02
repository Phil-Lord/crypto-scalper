import click
import matplotlib.pyplot as plt
import pandas as pd

from backtesting_engine import BacktestingEngine
from utils import get_second_timestamp, Pair, parse_datetime


@click.command()
@click.option('--pair', required=True, help='Trading pair (e.g. BTC)')
@click.option('--start', required=True, help='Start timestamp (e.g. 2025-1-1-0-0-0)')
@click.option('--end', required=True, help='End timestamp (e.g. 2025-1-1-23-59-59)')
@click.option('--strategy_name', required=True, help='Strategy name (e.g. sma)')
def run_backtest(pair: str, start: str, end: str, strategy_name: str) -> None:
    kraken_pair = Pair[pair].value
    start_timestamp = get_second_timestamp(*parse_datetime(start))
    end_timestamp = get_second_timestamp(*parse_datetime(end))
    params = {'short_window': 50, 'long_window': 200}

    engine = BacktestingEngine(kraken_pair, start_timestamp, end_timestamp, strategy_name, **params)
    engine.run()
    results = engine.get_strategy_results()
    print(results)
    plot_trade_results(results, pair)


def plot_trade_results(results: pd.DataFrame, pair: str) -> None:
    # Extract buys and sells.
    buys = results[results["signal"] == "buy"]
    sells = results[results["signal"] == "sell"]

    plt.figure(figsize=(12, 6))

    # Plot price.
    plt.plot(results.index, results["price"], label="Price", color="blue", alpha=0.4)

    # Plot SMAs.
    plt.plot(
        results.index,
        results['short_sma'],
        label='Short SMA',
        color='purple',
        linestyle='--'
    )
    plt.plot(
        results.index,
        results['long_sma'],
        label='Long SMA',
        color='green',
        linestyle='--'
    )

    # Plot buys and sells.
    plt.scatter(buys.index, buys["price"], color="green",
                label="Buy Signal", marker="^", alpha=1, s=100)
    plt.scatter(sells.index, sells["price"], color="red",
                label="Sell Signal", marker="v", alpha=1, s=100)

    # Titles, legends, etc.
    plt.title(f"Price Movement for {pair}")
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.show()


if __name__ == '__main__':
    run_backtest()
