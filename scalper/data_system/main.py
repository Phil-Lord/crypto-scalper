from pipelines import TradeDataPipeline
from utils import get_timestamp, Pair


def main():
    pair = Pair.BTC.value
    since = get_timestamp(2025, 1, 1, 0, 0, 0)
    until = get_timestamp(2025, 1, 10, 0, 0, 0)

    pipeline = TradeDataPipeline(pair, since, until)
    pipeline.get_trades()


if __name__ == '__main__':
    main()
