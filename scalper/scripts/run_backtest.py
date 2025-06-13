import click
import pandas as pd

from backtesting_engine import BacktestingEngine
from strategy_manager import StrategyManager
from utils import get_kraken_pair, get_second_timestamp, parse_datetime, plot_position_profits, plot_results, PRECISION_TREND_CONFIG, PRECISION_TREND_GRID

PARAMS = PRECISION_TREND_CONFIG
GRID = PRECISION_TREND_GRID
N_TRIALS = 100
INITIAL_QUOTE_BALANCE = 1000
PLOT_RESULTS = True


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
    ''' Run a backtest on the specified trading pair and strategy. '''
    # Create engine.
    engine = create_engine(pair, strategy_name, start, end, interval, vectorised)

    # Optimise parameters if requested.
    if optimise:
        engine = optimise_parameters(engine, strategy_name)

    # Run backtest.
    results = engine.run()
    output_results(engine, results, pair)


def create_engine(pair: str, strategy_name: str, start: str, end: str, interval: int, vectorised: bool) -> BacktestingEngine:
    ''' Create a backtesting engine with the specified parameters. '''
    kraken_pair = get_kraken_pair(pair)

    if start is not None:
        start = get_second_timestamp(*parse_datetime(start))
    if end is not None:
        end = get_second_timestamp(*parse_datetime(end))

    return BacktestingEngine(kraken_pair, strategy_name, start,
                             end, interval, vectorised, **PARAMS)


def optimise_parameters(engine: BacktestingEngine, strategy_name: str) -> BacktestingEngine:
    ''' Optimise parameters for the specified strategy. '''
    optimisation_results = engine.optimise_parameters(GRID, N_TRIALS)
    print(f'Best Parameters: {optimisation_results['best_params']}')
    print(f'Best Profit: {optimisation_results['best_profit']}')

    engine.strategy = StrategyManager().get_strategy(
        strategy_name, **optimisation_results['best_params'])

    return engine


def output_results(engine: BacktestingEngine, results: pd.DataFrame, pair: str) -> None:
    ''' Output the results of the backtest. '''
    print(f'Final Quote Balance: {engine.get_final_quote_balance(INITIAL_QUOTE_BALANCE)}')
    if (PLOT_RESULTS):
        position_profits = engine.calculate_position_profits(INITIAL_QUOTE_BALANCE)
        plot_results(results, pair)
        plot_position_profits(position_profits)


if __name__ == '__main__':
    run_backtest()
