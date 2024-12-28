import click

from market_data_fetcher import MarketDataFetcher
from strategy_runner import StrategyRunner
from trade_plotter import TradePlotter


@click.command()
@click.option('-b', '--base', default='ETH')
@click.option('-q', '--quote', default='GBP')
@click.option('-ib', '--initial-balance', default=500)
@click.option('-i', '--interval', default=1)
@click.option('-h', '--hours', default=8)
@click.option('-ss', '--sma-short', default=20)
@click.option('-sl', '--sma-long', default=100)
@click.option('-f', '--fee', default=0.004)
def backtester_start(base, quote, initial_balance, interval, hours, sma_short, sma_long, fee) -> None:
    """
    The CLI command to start a scalper backtest.

    :param str base: The base currency code.
    :param str quote: The quote currency code.
    :param int initial_balance: The initial quote currency balance.
    :param int interval: The amount of time to wait between performing the strategy (minutes).
    :param int hours: The number of hours to backtest for.
    :param int sma_short: The short Simple Moving Average window.
    :param int sma_long: The long Simple Moving Average window.
    :param float fee: The fee to apply to each transaction.
    """
    fetcher = MarketDataFetcher(base, quote, interval, hours, sma_long)
    data = fetcher.fetch_market_data()

    if not data.empty:
        runner = StrategyRunner(data, sma_short, sma_long, initial_balance, fee, hours)
        trading_data = runner.run_strategy()

        plotter = TradePlotter(trading_data, base, quote, sma_short, sma_long, initial_balance)
        plotter.output_position_results()
        plotter.output_results()
        plotter.plot()
    else:
        print("No data available for backtesting.")


if __name__ == "__main__":
    backtester_start()
