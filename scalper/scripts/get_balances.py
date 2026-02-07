import logging

from exchange_connector import BalanceConnector
from utils import LOG_FORMAT

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def get_balances() -> None:
    connector = BalanceConnector()
    result = connector.fetch()
    print(result)


if __name__ == '__main__':
    get_balances()
