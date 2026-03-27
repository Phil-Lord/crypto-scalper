from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import logging
import time

import pandas as pd

from data_system import Bot, BotRun, BotRunRepository, BotTickRepository, BotOrderRepository, OrderStatus
from exchange_connector import AddOrderConnector, BalanceConnector, OhlcConnector, QueryOrdersConnector, QueryOrderStatus
from .position_sizer import PairBalances, PositionSizer
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

        self.logger.info('TradeExecutor initialised')

    def warm_up(self) -> None:
        ''' Feeds historical OHLC data through the strategy to warm up indicators. '''
        self.logger.info('Warming up strategy...')

        candles = self._fetch_ohlc_history()
        if len(candles) < self.strategy.warmup_candles:
            self.logger.warning(
                f'Received {len(candles)} candles but {self.strategy.warmup_candles} required '
                f'(Kraken cap is 720); signals may be unreliable for the first few intervals'
            )

        for ohlc in candles:
            self.strategy.generate_signal(ohlc)
        self.logger.info(f'Warm-up complete: processed {len(candles)} candles')

    def shutdown(self) -> None:
        ''' Marks the bot run as complete. '''
        self.logger.info('Shutting down...')
        try:
            self.bot_run_repo.complete(self.run.id, datetime.now(timezone.utc))
        except Exception as e:
            self.logger.error(f'Failed to mark bot run complete: {e}', exc_info=True)
        self.logger.info('Shutdown complete')

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
            order_result = self.add_order_connector.place(self.bot.pair, signal, volume)
            self.logger.info(
                f'Trade executed: id={order_result.txid[0]}, order={order_result.order_description}')
            # TODO: Log execution price, volume, and fee.
        except Exception as e:
            self.logger.error(f'Trade execution failed: {e}', exc_info=True)

    def request_shutdown(self) -> None:
        ''' Signal the executor to stop after the current interval. '''
        self.logger.info('Shutdown requested')
        self._shutting_down = True

    def recover_state(self) -> None:
        ''' Sets latest directional action on strategy from database. '''
        latest_action = self.bot_tick_repo.get_latest_action_by_bot_id(self.bot.id)
        if latest_action:
            self.strategy.last_action = latest_action
            self.logger.info(f'Recovered last action: {latest_action}')
        else:
            self.logger.info('No previous action found, starting fresh')

    def _reconcile_placed_orders(self) -> None:
        placed_orders = self.bot_order_repo.get_placed_by_bot_id(self.bot.id)
        if not placed_orders:
            self.logger.info('No placed orders to reconcile')
            return

        orders_by_exchange_id = {order.exchange_order_id: order for order in placed_orders}
        exchange_orders = self.query_orders_connector.fetch(list(orders_by_exchange_id.keys()))

        for exchange_order in exchange_orders:
            try:
                order = orders_by_exchange_id[exchange_order.txid]
                if exchange_order.status == QueryOrderStatus.OPEN:
                    self.logger.info(f'Order {order.id} is still open on exchange')
                elif exchange_order.status == QueryOrderStatus.CLOSED:
                    self.bot_order_repo.update(replace(
                        order,
                        status=OrderStatus.FILLED,
                        filled_at=datetime.now(timezone.utc),
                        price=exchange_order.price,
                        volume=exchange_order.volume,
                        fee=exchange_order.fee
                    ))
                    self.logger.info(f'Order {order.id} marked as FILLED')
                elif exchange_order.status == QueryOrderStatus.CANCELED:
                    self.bot_order_repo.update(replace(
                        order,
                        status=OrderStatus.FAILED,
                        filled_at=datetime.now(timezone.utc),
                        price=exchange_order.price,
                        volume=exchange_order.volume,
                        fee=exchange_order.fee
                    ))
                    self.logger.info(f'Order {order.id} marked as FAILED (canceled on exchange)')
                else:
                    self.logger.warning(
                        f'Order {order.id} has unrecognized status {exchange_order.status}')
            except Exception as e:
                self.logger.error(
                    f'Failed to reconcile order {exchange_order.txid}: {e}', exc_info=True)

    def _fetch_ohlc(self) -> pd.Series:
        '''
        Fetches the latest completed OHLC candle as a Series with open, high, low, close keys.

        We use 2 intervals rather than 1: Kraken returns candles whose start timestamp >= since,
        and always appends the forming candle. With 1 interval back, the previous closed candle's
        start falls before since and is excluded, leaving only the forming candle duplicated at
        [-2] and [-1]. Two intervals back guarantees a distinct completed candle at [-2].
        '''
        since = int(time.time()) - self.bot.interval * 60 * 2
        candle = self.ohlc_connector.fetch(self.bot.pair, self.bot.interval, since)[-2]
        return pd.Series({
            'open': candle.open,
            'high': candle.high,
            'low': candle.low,
            'close': candle.close
        })

    def _fetch_ohlc_history(self) -> list[pd.Series]:
        '''
        Fetches completed historical OHLC candles for the warmup period.

        - Removes the final candle as Kraken always appends the currently-forming candle.
        - Requests 1 additional interval to compensate for `since` landing mid-interval.
        '''
        warmup_candles = self.strategy.warmup_candles
        since = int(time.time()) - self.bot.interval * 60 * (min(warmup_candles, 720) + 1)
        candles = self.ohlc_connector.fetch(self.bot.pair, self.bot.interval, since)[:-1]
        return [pd.Series({
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close
        }) for c in candles]

    def _fetch_balances(self) -> PairBalances:
        '''
        Fetches balances for the trading pair and returns them in a PairBalances dataclass.

        - If a balance is missing from the exchange response, it defaults to 0 to avoid errors.
        - Kraken returns balances as strings, but we convert to string before Decimal for safety.
        '''
        balances = self.balance_connector.fetch()
        return PairBalances(
            symbol_base=self.pair_symbols.base,
            symbol_quote=self.pair_symbols.quote,
            balance_base=Decimal(str(balances.get(self.pair_symbols.base, 0))),
            balance_quote=Decimal(str(balances.get(self.pair_symbols.quote, 0)))
        )
