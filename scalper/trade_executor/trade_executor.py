import logging

from data_system import Bot, BotRun, BotRunRepository, BotTickRepository, BotOrderRepository
from exchange_connector import AddOrderConnector, BalanceConnector, OhlcConnector, QueryOrdersConnector
from .position_sizer import PositionSizer
from strategy_manager import Strategy
from utils import get_kraken_pair_symbols


class BotLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        return f'[{self.extra["bot_id"]}] {msg}', kwargs


class TradeExecutor:
    def __init__(
            self, bot: Bot, strategy: Strategy, position_sizer: PositionSizer,
            bot_run_repo: BotRunRepository, bot_tick_repo: BotTickRepository,
            bot_order_repo: BotOrderRepository, balance_connector: BalanceConnector,
            ohlc_connector: OhlcConnector, add_order_connector: AddOrderConnector,
            query_orders_connector: QueryOrdersConnector, dry_run: bool = False
    ):
        self.bot = bot
        self.strategy = strategy
        self.position_sizer = position_sizer
        self.bot_run_repo = bot_run_repo
        self.bot_tick_repo = bot_tick_repo
        self.bot_order_repo = bot_order_repo
        self.balance_connector = balance_connector
        self.ohlc_connector = ohlc_connector
        self.add_order_connector = add_order_connector
        self.query_orders_connector = query_orders_connector
        self.dry_run = dry_run
        self._shutting_down = False

        self.logger = BotLoggerAdapter(logging.getLogger(__name__), {'bot_id': bot.id})
        self.pair_symbols = get_kraken_pair_symbols(bot.pair)
        self.run = self.bot_run_repo.add(BotRun(bot_id=bot.id))

        self.logger.info('Initialised TradeExecutor')

    def execute_interval(self) -> None:
        ''' Runs one trade decision cycle. '''
        try:
            price = self.get_price()
            signal = self.run_strategy(price)
            self.log_interval_results(price, signal)
            if signal != 'hold':
                self.execute_trade(signal)
        except Exception as e:
            self.logger.error(f'Error in TradeExecutor: {e}', exc_info=True)
            # TODO: Add an except which kills the loop when error is minimum balance not met.

    def get_price(self) -> float:
        ''' Call exchange connector to get price data. '''
        pass

    def run_strategy(self, price: float) -> str:
        ''' Call strategy manager to get trade signal. '''
        return self.strategy.generate_signal(price)['signal']

    def log_interval_results(self, price: float, signal: str):
        ''' Log the results of the interval. '''
        self.logger.info(f'Interval result: price={price:.2f}, signal={signal}')

    def execute_trade(self, signal: str):
        ''' Call exchange connector to add order. '''
        balances = self.balance_connector.fetch()
        if signal == 'buy':
            volume = balances[self.pair_symbols.quote]
        elif signal == 'sell':
            volume = balances[self.pair_symbols.base]

        try:
            self.logger.info(f'Placing {signal.upper()} order: volume={volume}')
            order_result = self.add_order_connector.place(self.pair, signal, volume)
            self.logger.info(
                f'Trade executed: id={order_result.txid[0]}, order={order_result.order_description}')
            # TODO: Log execution price, volume, and fee.
        except Exception as e:
            self.logger.error(f'Trade execution failed: {e}', exc_info=True)

    def request_shutdown(self):
        ''' Signal the executor to stop after the current interval. '''
        self.logger.info('Shutdown requested')
        self._shutting_down = True
