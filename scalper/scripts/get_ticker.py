import logging

import click

from exchange_connector import TickerConnector
from utils import LOG_FORMAT, get_kraken_pair

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


@click.command()
@click.option('--pair', '-p', required=True, help='Trading pair (e.g. BTCGBP)')
def get_ticker(pair: str) -> None:
    connector = TickerConnector()
    kraken_pair = get_kraken_pair(pair)
    result = connector.fetch(kraken_pair)
    print(result)


if __name__ == '__main__':
    get_ticker()
