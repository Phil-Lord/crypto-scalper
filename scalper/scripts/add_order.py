import click

from exchange_connector import AddOrderConnector, BalanceConnector
from utils import Pair


@click.command()
@click.option('--pair', required=True, help='Trading pair (e.g. BTC)')
@click.option('--signal', required=True, help='Signal (e.g. buy or sell)')
@click.option('--volume', required=True, help='Volume (Buy in quote, sell in base. -1 for all)')
def add_order(pair: str, signal: str, volume: float) -> None:
    if volume == '-1':
        volume = get_wallet_volume(signal)

    kraken_pair = Pair[pair].value
    add_order_connector = AddOrderConnector()
    result = add_order_connector.place(kraken_pair, signal, volume)
    print(result)


def get_wallet_volume(signal: str) -> float:
    balance_connector = BalanceConnector()
    balances = balance_connector.fetch()
    return balances['ZGBP'] if signal == 'buy' else balances['XXBT']


if __name__ == '__main__':
    add_order()
