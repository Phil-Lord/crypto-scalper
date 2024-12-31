import datetime
import time

from api import KrakenApiClient
from services import OhlcService, TradesService


def main():
    # test_ohlc()
    test_trades()


def test_ohlc():
    client = KrakenApiClient()
    service = OhlcService(client)

    since = datetime.datetime(2024, 12, 28, 16, 0, 0)
    since = int(time.mktime(since.timetuple()) * 1000000000)

    data = service.fetch_ohlc('XDGGBP', 1, since)
    print(data)


def test_trades():
    client = KrakenApiClient()
    service = TradesService(client)

    since = datetime.datetime(2024, 11, 28, 0, 0, 0)
    since = int(time.mktime(since.timetuple()) * 1000000000)

    until = datetime.datetime(2024, 12, 5, 22, 0, 0)
    until = int(time.mktime(until.timetuple()) * 1000000000)

    data = service.fetch_trades('XDGGBP', since, until)
    print(data)


if __name__ == '__main__':
    main()
