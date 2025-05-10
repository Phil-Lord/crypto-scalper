import time

from exchange_connector import AddOrderConnector, BalanceConnector, TickerConnector
from strategy_manager import StrategyManager


class TradeExecutor:
    def __init__(self, pair: str, interval: int, strategy_name: str, **strategy_params):
        self.pair = pair
        self.interval = interval
        self.ticker_connector = TickerConnector()
        self.balance_connector = BalanceConnector()
        self.add_order_connector = AddOrderConnector()
        self.strategy = StrategyManager().get_strategy(strategy_name, **strategy_params)

    def start(self) -> None:
        while True:
            price = self.get_price()
            signal = self.run_strategy(price)
            if signal != 'hold':
                self.execute_trade(signal)
            time.sleep(self.interval * 60)

    def get_price(self) -> float:
        ''' Call exchange connector to get ticker price data. '''
        return float(self.ticker_connector.fetch(self.pair)['c'][0])

    def run_strategy(self, price: float) -> str:
        ''' Call strategy manager to get trade signal. '''
        return self.strategy.generate_signal(price)['signal']

    def execute_trade(self, signal: str):
        ''' Call exchange connector to add order. '''
        balances = self.balance_connector.fetch()
        volume = balances['ZGBP'] if signal == 'buy' else balances['XXBT']
        order_result = self.add_order_connector.place(self.pair, signal, volume)

    def log_interval_results(self):
        ''' Log the results of the interval. '''
        # Time, ticker price, signal
        # If buy/sell: execution time, execution price, volume, fee, order Id
