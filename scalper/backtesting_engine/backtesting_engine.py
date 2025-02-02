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

    def run(self) -> pd.DataFrame:
        '''
        Load data from the database and run strategy evaluation on each minute.
        '''
        if self.minutely_data is None:
            self.__load_minutely_data()

        # Apply the strategy evaluation to each row.
        self.minutely_data['signal'] = self.minutely_data['price'].apply(self.strategy.evaluate)
        return self.minutely_data

    def get_strategy_results(self) -> pd.DataFrame:
        '''
        Get results composed by the strategy throughout the training run.
        '''
        return self.strategy.get_results()

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
