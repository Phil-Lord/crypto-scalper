import pandas as pd

from data_system import TradesRepository
from strategy_manager import StrategyManager


class BacktestingEngine:
    def __init__(self, pair: str, start: float, end: float, strategy_name: str, **strategy_params):
        self.pair = pair
        self.start = start
        self.end = end
        self.strategy = StrategyManager().get_strategy(strategy_name, **strategy_params)
        self.data = None

    def run(self) -> pd.DataFrame:
        if self.data is None:
            self.__load_data()

        # Apply the strategy evaluation to each row.
        self.data['signal'] = self.data['price'].apply(self.strategy.evaluate)
        return self.data

    def get_strategy_results(self) -> pd.DataFrame:
        return self.strategy.get_results()

    def __load_data(self) -> None:
        # Get trade data from the database using a Trades Repository.
        trades = TradesRepository().get(self.pair, self.start, self.end)

        # Convert timestamps to datetime format (retaining millisecond precision).
        trades["timestamp"] = pd.to_datetime(trades["timestamp"], unit="s")
        trades.set_index("timestamp", inplace=True)

        # Resample trades into minutely bins, keeping the last price of each minute.
        # If a minute has no trades, forward-fill it with the previous minute's price.
        self.data = trades.resample('1min').agg({'price': 'last'}).ffill()
