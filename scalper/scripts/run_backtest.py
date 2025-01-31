import click

from backtesting_engine import BacktestingEngine
from utils import get_second_timestamp, Pair, parse_datetime


@click.command()
@click.option('--pair', required=True, help='Trading pair (e.g. BTC)')
@click.option('--start', required=True, help='Start timestamp (e.g. 2025-1-1-0-0-0)')
@click.option('--end', required=True, help='End timestamp (e.g. 2025-1-1-23-59-59)')
@click.option('--strategy_name', required=True, help='Strategy name (e.g. sma)')
def run_backtest(pair: str, start: str, end: str, strategy_name: str) -> None:
    kraken_pair = Pair[pair].value
    start_timestamp = get_second_timestamp(*parse_datetime(start))
    end_timestamp = get_second_timestamp(*parse_datetime(end))
    params = {'window_size': 20}

    engine = BacktestingEngine(kraken_pair, start_timestamp, end_timestamp, strategy_name, **params)
    results = engine.run()

    print(results)


if __name__ == '__main__':
    run_backtest()
