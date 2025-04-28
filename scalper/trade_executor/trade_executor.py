from strategy_manager import StrategyManager


class TradeExecutor:
    def __init__(self, pair: str, interval: int, strategy_name: str, **strategy_params):
        self.pair = pair
        self.interval = interval
        self.strategy = StrategyManager().get_strategy(strategy_name, **strategy_params)

    def start(self):
        price = self.get_price()
        signal = self.run_strategy(price)
        self.execute_trade(signal)

    def get_price(self) -> float:
        ''' Call exchange connector to get ticker price data. '''
        pass

    def run_strategy(self, price: float) -> str:
        ''' Call strategy manager to get trade signal. '''
        result = self.strategy.generate_signal(price)
        return result.signal

    def execute_trade(self, signal: str):
        ''' Call exchange connector to add order. '''
        if (signal == 'buy'):
            print('buy')
        elif (signal == 'sell'):
            print('sell')
        elif (signal == 'hold'):
            print('hold')
