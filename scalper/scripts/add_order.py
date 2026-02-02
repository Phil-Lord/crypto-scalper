import click

from exchange_connector import AddOrderConnector, BalanceConnector
from utils import get_kraken_pair, get_kraken_pair_symbols


@click.command()
@click.option('--pair', required=True, help='Trading pair (e.g. BTCGBP)')
@click.option('--signal', required=True, help='Signal (e.g. buy or sell)')
@click.option('--volume', required=True, help='Volume (Buy in quote, sell in base. -1 for all)')
@click.option('--validate', '-v', is_flag=True, help='Validate order without executing')
def add_order(pair: str, signal: str, volume: float, validate: bool = False) -> None:
    kraken_pair = get_kraken_pair(pair)

    if volume == '-1':
        volume = get_wallet_volume(signal, kraken_pair)

    add_order_connector = AddOrderConnector()
    result = add_order_connector.place(kraken_pair, signal, volume, validate)
    print(f'Order placed: {result.txid}')
    print(f'Description: {result.order_description}')


def get_wallet_volume(signal: str, kraken_pair: str) -> float:
    balance_connector = BalanceConnector()
    balances = balance_connector.fetch()
    symbols = get_kraken_pair_symbols(kraken_pair)
    return balances[symbols['quote']] if signal == 'buy' else balances[symbols['base']]


if __name__ == '__main__':
    add_order()
