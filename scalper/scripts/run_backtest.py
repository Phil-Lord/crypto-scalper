import click
import pandas as pd

from backtesting_engine import BacktestingEngine
from strategy_manager import StrategyManager
from utils import get_second_timestamp, Pair, parse_datetime, plot_position_profits, plot_sma_results, SMA_GRID, SMA_50_200


@click.command()
@click.option('--pair', required=True, help='Trading pair (e.g. BTC)')
@click.option('--strategy_name', required=True, help='Strategy name (e.g. sma)')
@click.option('--start', required=False, help='Start timestamp (e.g. 2025-1-1-0-0-0)')
@click.option('--end', required=False, help='End timestamp (e.g. 2025-1-1-23-59-59)')
@click.option('--interval', required=False, help='Interval (e.g. 1, 3, 5, 15, etc.)')
@click.option('--vectorised', required=False, type=bool, help='Run in vectorised mode.')
@click.option('--optimise', is_flag=True, help='Enable parameter optimisation.')
def run_backtest(pair: str, strategy_name: str, start: str = None, end: str = None,
                 interval: int = 1, vectorised: bool = None, optimise: bool = False) -> None:
    engine = create_engine(pair, strategy_name, start, end, interval, vectorised)

    if optimise:
        engine = optimise_parameters(engine, strategy_name)

    results = engine.run()

    output_results(engine, results, pair)


def create_engine(pair: str, strategy_name: str, start: str, end: str, interval: int, vectorised: bool) -> BacktestingEngine:
    kraken_pair = Pair[pair].value
    params = SMA_50_200

    if start is not None:
        start = get_second_timestamp(*parse_datetime(start))
    if end is not None:
        end = get_second_timestamp(*parse_datetime(end))

    return BacktestingEngine(kraken_pair, strategy_name, start,
                             end, interval, vectorised, **params)


def optimise_parameters(engine: BacktestingEngine, strategy_name: str) -> BacktestingEngine:
    param_grid = SMA_GRID
    n_trials = 100

    optimisation_results = engine.optimise_parameters(param_grid, n_trials)
    print(f'Best Parameters: {optimisation_results['best_params']}')
    print(f'Best Profit: {optimisation_results['best_profit']}')

    engine.strategy = StrategyManager().get_strategy(
        strategy_name, **optimisation_results['best_params'])

    return engine


def output_results(engine: BacktestingEngine, results: pd.DataFrame, pair: str) -> None:
    print(f'Final Quote Balance: {engine.get_final_quote_balance(1000)}')
    position_profits = engine.calculate_position_profits(1000)
    plot_sma_results(results, pair)
    plot_position_profits(position_profits)


if __name__ == '__main__':
    run_backtest()
