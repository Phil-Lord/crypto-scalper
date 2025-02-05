import pandas as pd
from tqdm import tqdm

from data_system import TradesRepository
from strategy_manager import StrategyManager


class BacktestingEngine:
    def __init__(self, pair: str, strategy_name: str, start: float = None, end: float = None, **strategy_params):
        self.pair = pair
        self.start = start
        self.end = end
        self.strategy = StrategyManager().get_strategy(strategy_name, **strategy_params)
        self.minutely_data = None
        self.results = None

    def run(self) -> pd.DataFrame:
        '''
        Load data from the database and run strategy evaluation on each minute.
        '''
        if self.minutely_data is None:
            self.__load_minutely_data()

        results = []

        for row in self.minutely_data.itertuples(index=True, name='Row'):
            result = self.strategy.evaluate(row.price)
            result['price'] = row.price
            result['timestamp'] = row.Index
            results.append(result)

        self.results = pd.DataFrame(results).set_index('timestamp')
        return self.results

    def get_results(self) -> pd.DataFrame:
        '''
        Get results composed by the strategy throughout the training run.
        '''
        return self.results

    def __load_minutely_data(self) -> None:
        '''
        Load trade data from the database, indexed by timestamp (as datetimes).
        Then resample into minutely, forward-filled closing prices. 
        '''
        # Get trade data from the database using a Trades Repository.
        trades = TradesRepository().get(self.pair, self.start, self.end)

        # Convert timestamps to datetime format (retaining millisecond precision).
        trades["timestamp"] = pd.to_datetime(trades["timestamp"], unit="s")
        trades.set_index("timestamp", inplace=True)

        # Resample trades into minutely bins, keeping the last price of each minute.
        # If a minute has no trades, forward-fill it with the previous minute's price.
        self.minutely_data = trades.resample('1min').agg({'price': 'last'}).ffill()
