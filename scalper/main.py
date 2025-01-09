import csv
import datetime
import time

from api import KrakenApiClient
from services import OhlcService, TradesService

BITCOIN = 'XXBTZGBP'
DOGECOIN = 'XDGGBP'


def main():
    # test_ohlc()
    test_trades()


def test_ohlc():
    client = KrakenApiClient()
    service = OhlcService(client)

    since = convert_datetime_to_timestamp(2024, 12, 28, 16, 0, 0)

    data = service.fetch_ohlc(DOGECOIN, 1, since)
    print(data)


def test_trades():
    client = KrakenApiClient()
    service = TradesService(client)

    since = convert_datetime_to_timestamp(2023, 12, 31, 0, 0, 0)
    until = convert_datetime_to_timestamp(2025, 1, 5, 0, 0, 0)

    data = service.fetch_trades(BITCOIN, since, until)

    with open('trades.csv', 'w', newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for trade in data:
            writer.writerow(trade)


def convert_datetime_to_timestamp(year, month, day, hour, minute, second):
    date = datetime.datetime(year, month, day, hour, minute, second)
    return int(time.mktime(date.timetuple()) * 1000000000)


if __name__ == '__main__':
    main()
