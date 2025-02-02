import pandas as pd

from .base_strategy import Strategy


class SmaStrategy(Strategy):
    def __init__(self, short_window: int, long_window: int):
        super().__init__()
        self.short_window = short_window
        self.long_window = long_window
        self.last_signal = 'hold'

        # The rolling price data for the long window to be used during evaluation.
        self.rolling_prices = pd.DataFrame(columns=['price'])

        # The order and SMA results of a run for analysis.
        self.results = pd.DataFrame(columns=['price', 'short_sma', 'long_sma', 'signal'])

    def evaluate(self, price: float) -> str:
        # Roll prices and return 'hold' if there aren't enough to calculate the long SMA.
        ready_to_evaluate = self.__roll_prices(price)
        if not ready_to_evaluate:
            return 'hold'

        # Calculate SMAs and return signal.
        signal = self.__calculate_smas_for_signal(price)
        return signal

    def __roll_prices(self, price: float) -> bool:
        # Add the new price to the end of the long data window.
        self.rolling_prices.loc[len(self.rolling_prices)] = [price]

        # If the data exceeds the length of the long window, drop the oldest row.
        if len(self.rolling_prices) > self.long_window:
            self.rolling_prices = self.rolling_prices.iloc[1:].reset_index(drop=True)

        # If we don't have enough data to calculate the long SMA, add 'hold' to results.
        if len(self.rolling_prices) < self.long_window:
            self.results.loc[len(self.results)] = [price, None, None, 'hold']
            return False
        return True

    def __calculate_smas_for_signal(self, price: float) -> str:
        # Calculate the short-term and long-term SMAs.
        short_sma = self.rolling_prices['price'].tail(self.short_window).mean()
        long_sma = self.rolling_prices['price'].tail(self.long_window).mean()

        # Generate a signal based on the golden cross or death cross.
        if short_sma > long_sma and self.last_signal != 'buy':
            signal = 'buy'
            self.last_signal = 'buy'
        elif short_sma < long_sma and self.last_signal == 'buy':
            signal = 'sell'
            self.last_signal = 'sell'
        else:
            signal = 'hold'

        # Store the results.
        self.results.loc[len(self.results)] = [price, short_sma, long_sma, signal]
        return signal
