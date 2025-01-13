import csv

from pipelines import TradeDataPipeline
from utils import get_timestamp, Pair


def main():
    pair = Pair.BTC.value
    since = get_timestamp(2025, 1, 1, 0, 0, 0)
    until = get_timestamp(2025, 1, 10, 0, 0, 0)

    pipeline = TradeDataPipeline(pair, since, until)
    trades = pipeline.get_trades()

    with open('trades.csv', 'w', newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for trade in trades:
            writer.writerow(trade)


if __name__ == '__main__':
    main()
