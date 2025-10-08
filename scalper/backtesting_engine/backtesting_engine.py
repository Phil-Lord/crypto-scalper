import pandas as pd

from data_system import TradesRepository
from .profit_calculation import calculate_position_profits, get_final_quote_balance
from .parameter_optimisation import optimise_parameters
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
        self.ohlc_full = None
        self.ohlc_window = None
        self.results = None

    def run(self) -> pd.DataFrame:
        ''' Load trades from the database and generate a strategy signal for each interval. '''
        if self.ohlc_full is None:
            self._load_ohlc_data()

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

    def optimise_parameters(self, param_grid: dict[str, list[any]], n_trials: int = 100) -> dict[str, any]:
        if self.ohlc_full is None:
            self._load_ohlc_data()
        strategy_constraints = getattr(self.strategy.__class__, 'constraints', lambda: [])()
        return optimise_parameters(self, param_grid, n_trials, strategy_constraints)

    def calculate_position_profits(self, initial_quote_balance: float = 1000) -> float:
        if self.results is None:
            raise ValueError('Backtest yet to be ran, call run() first.')
        return calculate_position_profits(self.results, initial_quote_balance)

    def get_final_quote_balance(self, initial_quote_balance: float = 1000) -> float:
        if self.results is None:
            raise ValueError('Backtest yet to be ran, call run() first.')
        return get_final_quote_balance(self.results, initial_quote_balance)

    def set_ohlc_window(self, start: pd.Timestamp, end: pd.Timestamp) -> None:
        if self.ohlc_full is None:
            self._load_ohlc_data()
        self.ohlc_window = self.ohlc_full.loc[start:end]

    def _load_ohlc_data(self) -> None:
        '''
        Load trade data from the database, indexed by timestamp (as millisecond-precise datetimes).
        Then resample into forward-filled ohlc data for each interval.
        '''
        trades = TradesRepository().get(self.pair, self.start, self.end)
        trades["timestamp"] = pd.to_datetime(trades["timestamp"], unit="s")
        trades.set_index("timestamp", inplace=True)

        ohlc = trades['price'].resample(f'{self.interval}min').ohlc()
        ohlc = ohlc.bfill()
        ohlc.rename(columns={'close': 'price'}, inplace=True)
        self.ohlc_full = ohlc
        self.ohlc_window = ohlc
