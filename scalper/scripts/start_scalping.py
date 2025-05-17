import click

from trade_executor import TradeExecutor
from utils import Pair


@click.command()
@click.option('--pair', required=True, help='Trading pair (e.g. BTC)')
@click.option('--interval', required=False, type=int, help='Interval (e.g. 1, 3, 5, 15, etc.)')
@click.option('--strategy_name', required=True, help='Strategy name (e.g. SmaStrategy)')
def start_scalping(pair: str, interval: int, strategy_name: str) -> None:
    kraken_pair = Pair[pair].value
    params = {'short_window': 101, 'long_window': 1000}

    executor = TradeExecutor(kraken_pair, interval, strategy_name, **params)
    executor.start()


if __name__ == '__main__':
    start_scalping()
