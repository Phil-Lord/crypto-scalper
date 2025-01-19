from pipelines import TradeDbPipeline
from utils import get_timestamp, Pair


def main():
    pair = Pair.ETH.value
    since = get_timestamp(2025, 1, 1, 0, 0, 0)
    until = get_timestamp(2025, 1, 1, 23, 59, 59)

    pipeline = TradeDbPipeline(pair, since, until)
    pipeline.fetch_and_store_trades()


if __name__ == '__main__':
    main()
