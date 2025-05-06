from exchange_connector import BalanceConnector


def get_balances() -> None:
    connector = BalanceConnector()
    result = connector.fetch()
    print(result)


if __name__ == '__main__':
    get_balances()
