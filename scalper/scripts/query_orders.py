import logging

import click

from exchange_connector import QueryOrdersConnector
from utils import load_env, LOG_FORMAT

load_env()
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


@click.command()
@click.option('--txids', '-t', required=True, help='Comma-separated list of order IDs to query')
def query_orders(txids: str) -> None:
    query_orders_connector = QueryOrdersConnector()
    result = query_orders_connector.fetch(txids.split(','))

    for order in result:
        print(order)


if __name__ == '__main__':
    query_orders()
