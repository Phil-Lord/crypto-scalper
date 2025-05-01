import time

from exchange_connector import TickerConnector
from strategy_manager import StrategyManager


class TradeExecutor:
    def __init__(self, pair: str, interval: int, strategy_name: str, **strategy_params):
        self.pair = pair
        self.interval = interval
        self.connector = TickerConnector()
        self.strategy = StrategyManager().get_strategy(strategy_name, **strategy_params)

    def start(self) -> None:
        while True:
            price = self.get_price()
            signal = self.run_strategy(price)
            self.execute_trade(signal)
            time.sleep(self.interval * 60)

    def get_price(self) -> float:
        ''' Call exchange connector to get ticker price data. '''
        return float(self.connector.fetch(self.pair)['c'][0])

    def run_strategy(self, price: float) -> str:
        ''' Call strategy manager to get trade signal. '''
        result = self.strategy.generate_signal(price)
        return result['signal']

    def execute_trade(self, signal: str):
        ''' Call exchange connector to add order. '''
        if (signal == 'buy'):
            print('buy')
        elif (signal == 'sell'):
            print('sell')
        elif (signal == 'hold'):
            print('hold')
