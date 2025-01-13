import matplotlib.pyplot as plt


class TradePlotter:
    """
    Plots trading run data using matplotlib.
    """

    def __init__(self, data, base, quote, sma_short, sma_long, initial_balance):
        """
        Constructor.
        """
        self.data = data
        self.base = base
        self.quote = quote
        self.sma_short = sma_short
        self.sma_long = sma_long
        self.initial_balance = initial_balance

    def output_results(self):
        final_base_price = self.data['close'].iloc[-1]
        final_base_balance = self.data['wallet_base'].iloc[-1]
        final_quote_balance = self.data['wallet_quote'].iloc[-1]
        final_total_balance = final_quote_balance + (final_base_balance * final_base_price)
        net_profit = final_total_balance - self.initial_balance

        print(f'Final base balance:  {final_base_balance} {self.base.upper()}')
        print(f'Final quote balance: {final_quote_balance} {self.quote.upper()}')
        print(f'Net profit:          {net_profit} {self.quote.upper()}')

    def output_position_results(self):
        sell_gains = self.data[self.data['position'].notnull()]['position']
        print(sell_gains)

    def plot(self):
        plt.figure(figsize=(12, 6))

        self.__plot_price_and_sma()
        self.__plot_actions()
        self.__prepare_graph()
        plt.show()

    def __plot_price_and_sma(self):
        plt.plot(
            self.data['timestamp'],
            self.data['close'],
            label='Price',
            color='blue',
            linewidth=0.5
        )
        plt.plot(
            self.data['timestamp'],
            self.data['sma_short'],
            label=f'SMA ({self.sma_short})',
            color='green',
            linestyle='--'
        )
        plt.plot(
            self.data['timestamp'],
            self.data['sma_long'],
            label=f'SMA ({self.sma_long})',
            color='green',
            linestyle='--'
        )

    def __plot_actions(self):
        buys = self.data[self.data['action'] == 'buy']
        sells = self.data[self.data['action'] == 'sell']
        plt.scatter(buys['timestamp'], buys['close'], color='green', marker='^', label='Buy', s=100)
        plt.scatter(
            sells['timestamp'],
            sells['close'],
            color='red',
            marker='v',
            label='Sell',
            s=100
        )

    def __prepare_graph(self):
        plt.title(f'{self.base.upper()}/{self.quote.upper()} Price with SMAs and Trades')
        plt.xlabel('Time')
        plt.ylabel('Price')
        plt.legend()
        plt.grid()
