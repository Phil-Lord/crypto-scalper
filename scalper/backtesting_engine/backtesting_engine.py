import pandas as pd
from tqdm import tqdm

from data_system import TradesRepository
from .profit_calculation import calculate_position_profits, get_final_quote_balance
from .parameter_optimisation import optimise_parameters_postgres
from strategy_manager import StrategyManager


class BacktestingEngine:
    def __init__(self, pair: str, strategy_name: str, start: float = None, end: float = None,
                 interval: int = None, vectorised: bool = None, **strategy_params):
        self.pair = pair
        self.start = start
        self.end = end
        self.interval = interval if interval is not None else 1
        self.vectorised = vectorised if vectorised is not None else True
        self.strategy = StrategyManager().get_strategy(strategy_name, **strategy_params)
        self.resampled_prices = None
        self.results = None

    def run(self) -> pd.DataFrame:
        ''' Load trades from the database and generate a strategy signal for each interval. '''
        if self.resampled_prices is None:
            self.__load_resampled_prices()

        if self.vectorised:
            self.results = self.strategy.vectorised_compute(self.resampled_prices['price'])
        else:
            results = [None] * len(self.resampled_prices)
            for i, (timestamp, price) in enumerate(tqdm(self.resampled_prices['price'].items())):
                result = self.strategy.generate_signal(price)
                result.update({'price': price, 'timestamp': timestamp})
                results[i] = result
            self.results = pd.DataFrame(results).set_index('timestamp')

        return self.results

    def optimise_parameters(self, param_grid: dict[str, list[any]], n_trials: int = 100) -> dict[str, any]:
        if self.resampled_prices is None:
            self.__load_resampled_prices()
        return optimise_parameters_postgres(self, param_grid, n_trials)

    def get_results(self) -> pd.DataFrame:
        ''' Get price and indicator results from the backtesting run. '''
        return self.results

    def calculate_profit(self, initial_quote_balance: float = 1000) -> float:
        if self.results is None:
            raise ValueError('Backtest yet to be ran, call run() first.')
        return calculate_position_profits(self.results, initial_quote_balance)

    def get_final_quote_balance(self, initial_quote_balance: float = 1000) -> float:
        if self.results is None:
            raise ValueError('Backtest yet to be ran, call run() first.')
        return get_final_quote_balance(self.results, initial_quote_balance)

    def __load_resampled_prices(self) -> None:
        '''
        Load trade data from the database, indexed by timestamp (as millisecond-precise datetimes).
        Then resample into forward-filled closing prices for each interval.
        '''
        trades = TradesRepository().get(self.pair, self.start, self.end)
        trades["timestamp"] = pd.to_datetime(trades["timestamp"], unit="s")
        trades.set_index("timestamp", inplace=True)
        self.resampled_prices = trades.resample(
            f'{self.interval}min').agg({'price': 'last'}).ffill()
