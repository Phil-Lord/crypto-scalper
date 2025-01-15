from pipelines import TradeDataPipeline
from utils import get_timestamp, Pair


def main():
    pair = Pair.BTC.value
    since = get_timestamp(2025, 1, 4, 0, 0, 0)
    until = get_timestamp(2025, 1, 4, 23, 59, 59)

    pipeline = TradeDataPipeline(pair, since, until)
    pipeline.update_stored_trades()


if __name__ == '__main__':
    main()
