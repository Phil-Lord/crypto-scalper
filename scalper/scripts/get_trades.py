import logging

import click

from data_system import SQLAlchemyClient, SQLAlchemyTradeRepository
from utils import LOG_FORMAT, get_kraken_pair, get_second_timestamp, parse_datetime, plot_trade_data_from_db

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


@click.command()
@click.option('--pair', '-p', required=True, help='Trading pair (e.g. BTCGBP)')
@click.option('--start', '-s', required=False, help='Start timestamp (e.g. 2025-1-1-0-0-0)')
@click.option('--end', '-e', required=False, help='End timestamp (e.g. 2025-1-1-23-59-59)')
def get_trades(pair: str, start: str = None, end: str = None) -> None:
    client = SQLAlchemyClient()
    repository = SQLAlchemyTradeRepository(client)

    kraken_pair = get_kraken_pair(pair)
    if start is not None:
        start = get_second_timestamp(*parse_datetime(start))
    if end is not None:
        end = get_second_timestamp(*parse_datetime(end))

    trades = repository.get(kraken_pair, start, end)
    plot_trade_data_from_db(trades)


if __name__ == '__main__':
    get_trades()
