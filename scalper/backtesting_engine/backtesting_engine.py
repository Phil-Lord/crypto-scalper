import pandas as pd
from tqdm import tqdm

from data_system import TradesRepository
from strategy_manager import StrategyManager


class BacktestingEngine:
    def __init__(self, pair: str, strategy_name: str, start: float = None, end: float = None, interval: int = None, **strategy_params):
        self.pair = pair
        self.start = start
        self.end = end
        self.interval = interval if interval is not None else 1
        self.strategy = StrategyManager().get_strategy(strategy_name, **strategy_params)
        self.resampled_prices = None
        self.results = None

    def run(self) -> pd.DataFrame:
        ''' Load trades from the database and generate a strategy signal for each interval. '''
        if self.resampled_prices is None:
            self.__load_resampled_prices()

        results = []
        for row in tqdm(self.resampled_prices.itertuples(index=True, name='Row')):
            result = self.strategy.generate_signal(row.price)
            result.update({'price': row.price, 'timestamp': row.Index})
            results.append(result)

        self.results = pd.DataFrame(results).set_index('timestamp')
        return self.results

    def get_results(self) -> pd.DataFrame:
        ''' Get price and indicator results from the backtesting run. '''
        return self.results

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
