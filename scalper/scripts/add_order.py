import click

from exchange_connector import AddOrderConnector
from utils import Pair


@click.command()
@click.option('--pair', required=True, help='Trading pair (e.g. BTC)')
@click.option('--signal', required=True, help='Signal (e.g. buy or sell)')
def add_order(pair: str, signal: str) -> None:
    kraken_pair = Pair[pair].value
    connector = AddOrderConnector()
    result = connector.place(kraken_pair, signal)
    print(result)


if __name__ == '__main__':
    add_order()
