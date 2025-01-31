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

    def run(self):
        if self.data is None:
            self.__load_data()

    def __load_data(self) -> None:
        # Get trade data from the database using a Trades Repository.
        trades = TradesRepository().get(self.pair, self.start, self.end)

        # Convert timestamps to datetime format (retaining millisecond precision).
        trades["timestamp"] = pd.to_datetime(trades["timestamp"], unit="s")
        trades.set_index("timestamp", inplace=True)

        self.data = trades.resample('1T')
