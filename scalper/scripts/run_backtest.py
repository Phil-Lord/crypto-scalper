import click

from backtesting_engine import BacktestingEngine
from strategy_manager import StrategyManager
from utils import get_second_timestamp, Pair, parse_datetime, plot_position_profits, plot_sma_results, SMA_GRID


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
    kraken_pair = Pair[pair].value
    params = {'short_window': 403, 'long_window': 982}
    param_grid = SMA_GRID

    if start is not None:
        start = get_second_timestamp(*parse_datetime(start))
    if end is not None:
        end = get_second_timestamp(*parse_datetime(end))

    engine = BacktestingEngine(kraken_pair, strategy_name, start,
                               end, interval, vectorised, **params)

    if optimise:
        optimisation_results = engine.optimise_parameters(param_grid, 100)

        print("Best Parameters:", optimisation_results['best_params'])
        print("Best Profit:", optimisation_results['best_profit'])

        engine.strategy = StrategyManager().get_strategy(
            strategy_name, **optimisation_results['best_params'])

    results = engine.run()
    position_profits = engine.calculate_profit(1000)

    plot_sma_results(results, pair)
    plot_position_profits(position_profits)


if __name__ == '__main__':
    run_backtest()
