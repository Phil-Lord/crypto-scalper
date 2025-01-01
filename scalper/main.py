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

    since = convert_datetime_to_timestamp(2024, 12, 28, 16, 0, 0)

    data = service.fetch_ohlc('XDGGBP', 1, since)
    print(data)


def test_trades():
    client = KrakenApiClient()
    service = TradesService(client)

    since = convert_datetime_to_timestamp(2024, 12, 25, 0, 0, 0)
    until = convert_datetime_to_timestamp(2024, 12, 30, 23, 59, 59)

    data = service.fetch_trades('XXBTZGBP', since, until)
    print(data)


def convert_datetime_to_timestamp(year, month, day, hour, minute, second):
    date = datetime.datetime(year, month, day, hour, minute, second)
    return int(time.mktime(date.timetuple()) * 1000000000)


if __name__ == '__main__':
    main()
