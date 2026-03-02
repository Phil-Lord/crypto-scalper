import logging
import os

from exchange_connector import AddOrderConnector, BalanceConnector, TickerConnector
from strategy_manager import Strategy
from utils import load_env, LOG_FORMAT, get_kraken_pair_symbols


load_env()
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)


class TradeExecutor:
    def __init__(self, pair: str, interval: int, strategy: Strategy):
        self.pair = pair
        self.symbols = get_kraken_pair_symbols(pair)
        self.interval = interval
        self.ticker_connector = TickerConnector()
        self.balance_connector = BalanceConnector()
        self.add_order_connector = AddOrderConnector()
        self.strategy = strategy
        logger.info(f'Initialised TradeExecutor: {pair} - {strategy.__class__.__name__}')

    def execute_interval(self) -> None:
        ''' Runs one trade decision cycle. '''
        try:
            price = self.get_price()
            signal = self.run_strategy(price)
            self.log_interval_results(price, signal)
            if signal != 'hold':
                self.execute_trade(signal)
        except Exception as e:
            logger.error(f'Error in TradeExecutor: {e}', exc_info=True)
            # TODO: Add an except which kills the loop when error is minimum balance not met.

    def get_price(self) -> float:
        ''' Call exchange connector to get ticker price data. '''
        return float(self.ticker_connector.fetch(self.pair)['c'][0])

    def run_strategy(self, price: float) -> str:
        ''' Call strategy manager to get trade signal. '''
        return self.strategy.generate_signal(price)['signal']

    def log_interval_results(self, price: float, signal: str):
        ''' Log the results of the interval. '''
        logger.info(f'Interval result: price={price:.2f}, signal={signal}')

    def execute_trade(self, signal: str):
        ''' Call exchange connector to add order. '''
        balances = self.balance_connector.fetch()
        if signal == 'buy':
            volume = balances[self.symbols.quote]
        elif signal == 'sell':
            volume = balances[self.symbols.base]

        try:
            logger.info(f'Placing {signal.upper()} order: volume={volume}')
            order_result = self.add_order_connector.place(self.pair, signal, volume)
            logger.info(
                f'Trade executed: id={order_result.txid[0]}, order={order_result.order_description}')
            # TODO: Log execution price, volume, and fee.
        except Exception as e:
            logger.error(f'Trade execution failed: {e}', exc_info=True)
