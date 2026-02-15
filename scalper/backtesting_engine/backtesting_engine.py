from typing import Any

import pandas as pd

from strategy_manager import Strategy
from data_system import TradeRepository

from .profit_calculation import calculate_position_profits, get_final_quote_balance
from .parameter_optimisation import optimise_parameters


class BacktestingEngine:
    '''
    Backtesting engine for evaluating trading strategies on historical data.

    Loads trade data from a repository, resamples into OHLC windows, and runs
    a strategy to generate trading signals. Supports both vectorised (fast batch
    processing for optimisation) and iterative (row-by-row) execution modes.
    '''

    def __init__(
            self, pair: str, strategy: Strategy, repository: TradeRepository, start: float = None,
            end: float = None, interval: int = None, vectorised: bool = None
    ):
        self.pair = pair
        self.start = start
        self.end = end
        self.interval = interval if interval is not None else 1
        self.vectorised = vectorised if vectorised is not None else True
        self.strategy = strategy
        self.ohlc_full = None
        self.ohlc_window = None
        self.results = None
        self._load_ohlc_data(repository)

    def run(self) -> pd.DataFrame:
        ''' Execute the strategy on the loaded OHLC data to generate trading signals. '''
        if self.vectorised:
            self.results = self.strategy.vectorised_compute(self.ohlc_window)
        else:
            results = [None] * len(self.ohlc_window)
            for i, (timestamp, row) in enumerate(self.ohlc_window.iterrows()):
                result = self.strategy.generate_signal(row)
                result.update({'timestamp': timestamp})
                results[i] = result
            self.results = pd.DataFrame(results).set_index('timestamp')

        return self.results

    def optimise_parameters(self, param_grid: dict[str, list[Any]], n_trials: int = 100) -> None:
        strategy_constraints = getattr(self.strategy.__class__, 'constraints', lambda: [])()
        optimise_parameters(self, param_grid, n_trials, strategy_constraints)

    def calculate_position_profits(self, initial_quote_balance: float = 1000) -> pd.DataFrame:
        if self.results is None:
            raise ValueError('Backtest yet to be ran, call run() first.')
        return calculate_position_profits(self.results, initial_quote_balance)

    def get_final_quote_balance(self, initial_quote_balance: float = 1000) -> float:
        if self.results is None:
            raise ValueError('Backtest yet to be ran, call run() first.')
        return get_final_quote_balance(self.results, initial_quote_balance)

    def set_ohlc_window(self, start: pd.Timestamp = None, end: pd.Timestamp = None) -> None:
        if start is None or end is None:
            self.ohlc_window = self.ohlc_full
        else:
            self.ohlc_window = self.ohlc_full.loc[start:end]

    def _load_ohlc_data(self, repository: TradeRepository) -> None:
        '''
        Load trade data from the database, indexed by timestamp (as millisecond-precise datetimes).
        Then resample into forward-filled ohlc data for each interval.
        '''
        trade_list = repository.get(self.pair, self.start, self.end)

        if not trade_list:
            raise ValueError(f'No trades found for {self.pair} in the specified time range.')

        trades = pd.DataFrame([
            {'timestamp': t.timestamp, 'price': t.price}
            for t in trade_list
        ])
        trades['timestamp'] = pd.to_datetime(trades['timestamp'], unit='s')
        trades.set_index('timestamp', inplace=True)

        ohlc = trades['price'].resample(f'{self.interval}min').ohlc()
        ohlc = ohlc.bfill()
        ohlc.rename(columns={'close': 'price'}, inplace=True)
        self.ohlc_full = ohlc
        self.ohlc_window = ohlc
