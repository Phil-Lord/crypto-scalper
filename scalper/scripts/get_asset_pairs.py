import logging

import click

from exchange_connector import AssetPairsConnector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)


@click.command()
@click.option('--pair', '-p', required=True, help='Trading pair (e.g. BTCGBP)')
def get_asset_pairs(pair: str) -> None:
    connector = AssetPairsConnector()
    result = connector.fetch(pair)
    print(result)


if __name__ == '__main__':
    get_asset_pairs()
