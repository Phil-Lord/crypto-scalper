import click

from data_system import TradesRepository
from utils import get_second_timestamp, Pair, parse_datetime, plot_trade_data_from_db


@click.command()
@click.option('--pair', required=True, help='Trading pair (e.g. BTC)')
@click.option('--start', required=False, help='Start timestamp (e.g. 2025-1-1-0-0-0)')
@click.option('--end', required=False, help='End timestamp (e.g. 2025-1-1-23-59-59)')
def fetch_trades(pair: str, start: str = None, end: str = None) -> None:
    repository = TradesRepository()

    kraken_pair = Pair[pair].value
    if start is not None:
        start = get_second_timestamp(*parse_datetime(start))
    if end is not None:
        end = get_second_timestamp(*parse_datetime(end))

    trades = repository.get(kraken_pair, start, end)
    plot_trade_data_from_db(trades)


if __name__ == '__main__':
    fetch_trades()
