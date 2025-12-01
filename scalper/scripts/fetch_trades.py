import click

from data_system import SQLAlchemyClient, TradesService
from exchange_connector import TradesConnector
from utils import get_kraken_pair, get_nano_timestamp, parse_datetime


@click.command()
@click.option('--pair', '-p', required=True, help='Trading pair (e.g. BTCGBP)')
@click.option('--start', '-s', required=True, help='Start timestamp (e.g. 2025-1-1-0-0-0)')
@click.option('--end', '-e', required=True, help='End timestamp (e.g. 2025-1-1-23-59-59)')
def fetch_trades(pair: str, start: str, end: str) -> None:
    connector = TradesConnector()
    client = SQLAlchemyClient()
    service = TradesService(client)

    kraken_pair = get_kraken_pair(pair)
    start_timestamp = get_nano_timestamp(*parse_datetime(start))
    end_timestamp = get_nano_timestamp(*parse_datetime(end))

    trades = connector.fetch(kraken_pair, start_timestamp, end_timestamp)
    service.add(trades, kraken_pair)


if __name__ == '__main__':
    fetch_trades()
