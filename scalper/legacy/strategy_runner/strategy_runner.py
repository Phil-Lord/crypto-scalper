import pandas as pd


class StrategyRunner:
    """
    Runs the SMA strategy.
    """

    def __init__(self, data, sma_short, sma_long, initial_balance, fee, trading_hours) -> None:
        """
        Constructor.
        """
        self.data = data
        self.sma_short = sma_short
        self.sma_long = sma_long
        self.wallet_quote = initial_balance
        self.wallet_base = 0
        self.fee = fee
        self.trading_hours = trading_hours
        self.in_position = False
        self.previous_buy_cost = 0

    def run_strategy(self) -> pd.DataFrame:
        """
        Run the strategy.
        """
        self.__prepare_data_for_trading()

        for i in range(len(self.data)):
            price = self.data['close'].iloc[i]
            sma_short = self.data['sma_short'].iloc[i]
            sma_long = self.data['sma_long'].iloc[i]

            # Get previous SMAs to check for crosses.
            sma_short_prev = self.data['sma_short'].iloc[i - 1] if i > 0 else None
            sma_long_prev = self.data['sma_long'].iloc[i - 1] if i > 0 else None

            # Buy at the start of the trading session.
            if i == 0:
                self.__buy(price, i)
            elif sma_short > sma_long and sma_short_prev <= sma_long_prev and not self.in_position:
                self.__buy(price, i)
            elif sma_short < sma_long and sma_short_prev >= sma_long_prev and self.in_position:
                self.__sell(price, i)

            self.data.at[i, 'wallet_quote'] = self.wallet_quote
            self.data.at[i, 'wallet_base'] = self.wallet_base

        return self.data

    def __prepare_data_for_trading(self) -> None:
        # Add short and long moving average columns to data.
        self.data['sma_short'] = self.data['close'].rolling(window=self.sma_short).mean()
        self.data['sma_long'] = self.data['close'].rolling(window=self.sma_long).mean()

        # Trim data to trading period (last `trading_hours` hours).
        # Any data before the `cutoff_time` is needed for the long SMA, but not for trading.
        cutoff_time = self.data['timestamp'].iloc[-1] - pd.Timedelta(hours=self.trading_hours)
        self.data = self.data[self.data['timestamp'] > cutoff_time]
        self.data.reset_index(drop=True, inplace=True)

        # Add columns for the trade results of each interval.
        self.data['action'] = None
        self.data['wallet_quote'] = None
        self.data['wallet_base'] = None
        self.data['position'] = None

    def __buy(self, price, row):
        self.previous_buy_cost = self.wallet_quote
        self.wallet_base = (self.wallet_quote * (1 - self.fee)) / price
        self.wallet_quote = 0
        self.data.at[row, 'action'] = 'buy'
        self.in_position = True

    def __sell(self, price, row):
        self.wallet_quote = self.wallet_base * price * (1 - self.fee)
        self.wallet_base = 0
        self.data.at[row, 'action'] = 'sell'
        self.data.at[row, 'position'] = self.previous_buy_cost - self.wallet_quote
        self.in_position = False
        self.previous_buy_cost = 0
