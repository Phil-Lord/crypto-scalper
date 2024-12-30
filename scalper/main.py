import datetime
import time

from api import KrakenApiClient
from services import OhlcService


def main():
    client = KrakenApiClient()
    service = OhlcService(client)

    since = datetime.datetime(2024, 12, 28, 16, 0, 0)
    since = int(time.mktime(since.timetuple()) * 1000000000)
    print(service.fetch_ohlc('XDGGBP', 1, since))


if __name__ == '__main__':
    main()
