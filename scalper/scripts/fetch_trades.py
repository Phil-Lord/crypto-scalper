import click

from exchange_connector import TradesConnector
from utils import get_timestamp, Pair, parse_datetime


@click.command()
@click.option('--pair', required=True, help='Trading pair (e.g. BTC)')
@click.option('--start', required=True, help='Start timestamp (e.g. 2025-1-1-0-0-0)')
@click.option('--end', required=True, help='End timestamp (e.g. 2025-1-1-23-59-59)')
def fetch_trades(pair: str, start: str, end: str) -> None:
    connector = TradesConnector()

    kraken_pair = Pair[pair].value
    start_timestamp = get_timestamp(*parse_datetime(start))
    end_timestamp = get_timestamp(*parse_datetime(end))

    trades = connector.fetch(kraken_pair, start_timestamp, end_timestamp)


if __name__ == '__main__':
    fetch_trades()
