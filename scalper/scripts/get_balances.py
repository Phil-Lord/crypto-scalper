import logging

from exchange_connector import BalanceConnector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)


def get_balances() -> None:
    connector = BalanceConnector()
    result = connector.fetch()
    print(result)


if __name__ == '__main__':
    get_balances()
