import click
import pandas as pd

from backtesting_engine import BacktestingEngine
from data_system import SqlAlchemyTradeRepository
from utils import get_kraken_pair, get_second_timestamp, parse_datetime, plot_position_profits, plot_results, SMA_CONFIG, SMA_GRID, PRECISION_TREND_CONFIG, PRECISION_TREND_GRID

USE_DEFAULT_STRATEGY_CONFIGS = True
PARAMS = PRECISION_TREND_CONFIG
GRID = PRECISION_TREND_GRID
N_TRIALS = 1000
INITIAL_QUOTE_BALANCE = 1000
PLOT_RESULTS = True


@click.command()
@click.option('--pair', '-p', required=True, help='Trading pair (e.g. BTC)')
@click.option('--strategy_name', '-sn', required=True, help='Strategy name (e.g. sma)')
@click.option('--start', '-s', required=False, help='Start timestamp (e.g. 2025-1-1-0-0-0)')
@click.option('--end', '-e', required=False, help='End timestamp (e.g. 2025-1-1-23-59-59)')
@click.option('--interval', '-i', required=False, help='Interval (e.g. 1, 3, 5, 15, etc.)')
@click.option('--vectorised', '-v', is_flag=True, help='Run in vectorised mode.')
@click.option('--optimise', '-o', is_flag=True, help='Enable parameter optimisation.')
def run_backtest(pair: str, strategy_name: str, start: str = None, end: str = None,
                 interval: int = 1, vectorised: bool = False, optimise: bool = False) -> None:
    ''' Run a backtest on the specified trading pair and strategy. '''
    params, grid = get_params_for_strategy(strategy_name)
    engine = create_engine(pair, strategy_name, start, end, interval, vectorised, **params)

    if optimise:
        engine.optimise_parameters(grid, N_TRIALS)
    else:
        results = engine.run()
        output_results(engine, results, pair)


def get_params_for_strategy(strategy_name: str) -> tuple:
    ''' Get the default parameters and grid for the specified strategy. '''
    if not USE_DEFAULT_STRATEGY_CONFIGS:
        return PARAMS, GRID
    if strategy_name == 'SmaStrategy':
        return SMA_CONFIG, SMA_GRID
    elif strategy_name == 'PrecisionTrendStrategy':
        return PRECISION_TREND_CONFIG, PRECISION_TREND_GRID


def create_engine(pair: str, strategy_name: str, start: str, end: str, interval: int, vectorised: bool, **params) -> BacktestingEngine:
    ''' Create a backtesting engine with the specified parameters. '''
    kraken_pair = get_kraken_pair(pair)
    repository = SqlAlchemyTradeRepository()

    if start is not None:
        start = get_second_timestamp(*parse_datetime(start))
    if end is not None:
        end = get_second_timestamp(*parse_datetime(end))

    return BacktestingEngine(kraken_pair, strategy_name, repository, start, end,
                             interval, vectorised, **params)


def output_results(engine: BacktestingEngine, results: pd.DataFrame, pair: str) -> None:
    ''' Output the results of the backtest. '''
    print(f'Final Quote Balance: {engine.get_final_quote_balance(INITIAL_QUOTE_BALANCE)}')
    if PLOT_RESULTS:
        print('No. trades:', results['signal'].ne('hold').sum())
        position_profits = engine.calculate_position_profits(INITIAL_QUOTE_BALANCE)
        plot_results(results, pair)
        plot_position_profits(position_profits)


if __name__ == '__main__':
    run_backtest()
