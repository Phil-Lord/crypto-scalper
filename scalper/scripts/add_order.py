import logging
from decimal import Decimal

import click

from exchange_connector import AddOrderConnector, BalanceConnector
from utils import load_env, LOG_FORMAT, get_kraken_pair, get_kraken_pair_symbols

load_env()
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


@click.command()
@click.option('--pair', required=True, help='Trading pair (e.g. BTCGBP)')
@click.option('--signal', required=True, help='Signal (e.g. buy or sell)')
@click.option('--volume', required=True, help='Volume (Buy in quote, sell in base. -1 for all)')
@click.option('--validate', '-v', is_flag=True, help='Validate order without executing')
def add_order(pair: str, signal: str, volume: str, validate: bool = False) -> None:
    kraken_pair = get_kraken_pair(pair)

    decimal_volume = get_wallet_volume(signal, kraken_pair) if volume == '-1' else Decimal(volume)

    add_order_connector = AddOrderConnector()
    result = add_order_connector.place(kraken_pair, signal, decimal_volume, validate)
    print(f'Order placed: {result.txid}')
    print(f'Description: {result.order_description}')


def get_wallet_volume(signal: str, kraken_pair: str) -> Decimal:
    balance_connector = BalanceConnector()
    balances = balance_connector.fetch()
    symbols = get_kraken_pair_symbols(kraken_pair)
    raw_volume = balances[symbols.quote] if signal == 'buy' else balances[symbols.base]
    return Decimal(str(raw_volume))  # Convert to string to avoid float precision issues


if __name__ == '__main__':
    add_order()
