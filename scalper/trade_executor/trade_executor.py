from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import logging
import time

import pandas as pd

from data_system import Bot, BotOrder, BotRun, BotTick, BotRunRepository, BotTickRepository, BotOrderRepository, OrderStatus, Side, Signal
from exchange_connector import AddOrderConnector, BalanceConnector, OhlcCandle, OhlcConnector, QueryOrdersConnector, QueryOrderResult, QueryOrderStatus
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

        self.logger.info(f'TradeExecutor initialised (run_id={self.run.id})')

    def recover_state(self) -> None:
        '''
        Restores strategy.last_action from the most recent bot tick in the database.

        If the tick's associated order failed, the action is reversed (the position
        never actually changed). Defaults to SELL if no previous tick exists.
        '''
        latest_tick = self.bot_tick_repo.get_latest_action_by_bot_id(self.bot.id)
        if latest_tick:
            associated_order = self.bot_order_repo.get_by_tick_id(latest_tick.id)
            if associated_order and associated_order.status == OrderStatus.FAILED:
                actual_action = Signal.SELL if latest_tick.signal == Signal.BUY else Signal.BUY
                self.strategy.last_action = actual_action
                self.logger.info(
                    f'Recovered last action: {actual_action.value} '
                    f'(reversed from {latest_tick.signal.value} — order {associated_order.id} FAILED)'
                )
            else:
                self.strategy.last_action = latest_tick.signal
                self.logger.info(f'Recovered last action: {latest_tick.signal.value}')
        else:
            self.strategy.last_action = Signal.SELL
            self.logger.info('No previous action found, starting fresh')

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

    def execute_interval(self) -> None:
        '''
        Executes a single interval of the bot's strategy:

        1. Reconciles any previously placed orders against the exchange.
        2. Fetches the latest completed OHLC candle.
        3. Generates a signal and places an order if BUY/SELL.
        4. Persists a tick with signal, balances, and any errors (skipped in dry-run mode).

        No-ops if a shutdown has been requested. Returns early if OHLC data is unavailable.
        '''
        if self._shutting_down:
            self.logger.info('Shutdown in progress, skipping interval execution')
            return

        try:
            self._reconcile_placed_orders()
        except Exception as e:
            self.logger.error(f'Failed to reconcile placed orders: {e}', exc_info=True)

        try:
            ohlc = self._fetch_ohlc()
        except Exception as e:
            self.logger.error(f'Failed to fetch OHLC data: {e}', exc_info=True)
            return

        result = self._execute_signal(ohlc)
        if result is None:
            return

        signal, placed_order, balances, tick_error = result

        if self.dry_run:
            level = logging.DEBUG if signal == Signal.HOLD else logging.INFO
            self.logger.log(
                level,
                f'[DRY RUN] signal={signal.value}, price={ohlc["close"]}, '
                f'balance_base={balances.balance_base}, balance_quote={balances.balance_quote}',
            )
            return

        self._persist_results(ohlc, signal, balances, tick_error, placed_order)

    def request_shutdown(self) -> None:
        ''' Signal the executor to stop after the current interval. '''
        self.logger.info('Shutdown requested')
        self._shutting_down = True

    def shutdown(self) -> None:
        ''' Marks the bot run as complete. '''
        self.logger.info('Shutting down...')
        try:
            self.bot_run_repo.complete(self.run.id, datetime.now(timezone.utc))
        except Exception as e:
            self.logger.error(f'Failed to mark bot run complete: {e}', exc_info=True)
        self.logger.info('Shutdown complete')

    def _reconcile_placed_orders(self) -> None:
        '''
        Queries the exchange for the status of all PLACED orders for this bot, settles each as
        FILLED or FAILED, and rolls back strategy.last_action if an order was cancelled/expired.

        Logs a warning for any order not returned by the exchange.
        '''
        placed_orders = self.bot_order_repo.get_placed_by_bot_id(self.bot.id)
        if not placed_orders:
            self.logger.debug('No placed orders to reconcile')
            return

        self.logger.info(f'Reconciling {len(placed_orders)} placed order(s)')
        orders_by_exchange_id = {order.exchange_order_id: order for order in placed_orders}
        exchange_orders = self.query_orders_connector.fetch(list(orders_by_exchange_id.keys()))

        for exchange_order in exchange_orders:
            try:
                order = orders_by_exchange_id[exchange_order.txid]
                self._reconcile_order(order, exchange_order)
            except Exception as e:
                self.logger.error(
                    f'Failed to reconcile order {exchange_order.txid}: {e}', exc_info=True)

        returned_txids = {exchange_order.txid for exchange_order in exchange_orders}
        for exchange_id, order in orders_by_exchange_id.items():
            if exchange_id not in returned_txids:
                self.logger.warning(
                    f'Order {order.id} (txid={exchange_id}) not returned by exchange')

    def _reconcile_order(self, order: BotOrder, exchange_order: QueryOrderResult) -> None:
        '''
        Settles a single order via _settle_order. No-ops if still open/pending.
        If the order was cancelled/expired, rolls back strategy.last_action to
        the opposite signal (the position change never happened).
        '''
        if exchange_order.status in (QueryOrderStatus.PENDING, QueryOrderStatus.OPEN):
            self.logger.info(
                f'Order {order.id} is still open on the exchange '
                f'with status {exchange_order.status.value}')
            return

        settled = self._settle_order(order, exchange_order)
        if settled is None:
            self.logger.warning(
                f'Order {order.id} has unrecognised status {exchange_order.status.value}')
            return

        if exchange_order.status in (QueryOrderStatus.CANCELED, QueryOrderStatus.EXPIRED):
            if self.strategy.last_action == Signal(order.side.value):
                opposite = Signal.SELL if order.side == Side.BUY else Signal.BUY
                self.strategy.last_action = opposite
                self.logger.warning(
                    f'Rolled back strategy last_action to {opposite.value} '
                    f'(order {order.id}, txid={exchange_order.txid})')

    def _settle_order(self, order: BotOrder, exchange_order: QueryOrderResult) -> BotOrder | None:
        '''
        Updates an order's status based on exchange query results.

        :return: Updated order if settled (FILLED/FAILED), None if still open/pending.
        '''
        if exchange_order.status == QueryOrderStatus.CLOSED:
            updated = self.bot_order_repo.mark_filled(
                order.id, exchange_order.price, exchange_order.volume, exchange_order.fee)
            self.logger.info(
                f'Order {order.id} (txid={exchange_order.txid}) marked as FILLED '
                f'(price={exchange_order.price}, volume={exchange_order.volume}, fee={exchange_order.fee})')
            return updated
        if exchange_order.status in (QueryOrderStatus.CANCELED, QueryOrderStatus.EXPIRED):
            updated = self.bot_order_repo.mark_failed(
                order.id, exchange_order.price, exchange_order.volume, exchange_order.fee)
            self.logger.warning(
                f'Order {order.id} (txid={exchange_order.txid}) marked as FAILED '
                f'({exchange_order.status.value}, price={exchange_order.price}, '
                f'volume={exchange_order.volume}, fee={exchange_order.fee})')
            return updated
        return None

    @staticmethod
    def _candle_to_series(candle: OhlcCandle) -> pd.Series:
        return pd.Series({
            'open': candle.open,
            'high': candle.high,
            'low': candle.low,
            'close': candle.close,
        })

    def _fetch_ohlc(self) -> pd.Series:
        '''
        Fetches the latest completed OHLC candle as a Series with open, high, low, close keys.

        We use 2 intervals rather than 1: Kraken returns candles whose start timestamp >= since,
        and always appends the forming candle. With 1 interval back, the previous closed candle's
        start falls before since and is excluded, leaving only the forming candle duplicated at
        [-2] and [-1]. Two intervals back guarantees a distinct completed candle at [-2].
        '''
        since = int(time.time()) - self.bot.interval * 60 * 2
        candles = self.ohlc_connector.fetch(self.bot.pair, self.bot.interval, since)
        if len(candles) < 2:
            raise ValueError(f'Expected at least 2 OHLC candles but got {len(candles)}')
        return self._candle_to_series(candles[-2])

    def _fetch_ohlc_history(self) -> list[pd.Series]:
        '''
        Fetches completed historical OHLC candles for the warmup period.

        - Removes the final candle as Kraken always appends the currently-forming candle.
        - Requests 1 additional interval to compensate for `since` landing mid-interval.
        '''
        warmup_candles = self.strategy.warmup_candles
        since = int(time.time()) - self.bot.interval * 60 * (min(warmup_candles, 720) + 1)
        candles = self.ohlc_connector.fetch(self.bot.pair, self.bot.interval, since)[:-1]
        return [self._candle_to_series(c) for c in candles]

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

    def _execute_signal(
            self, ohlc: pd.Series,
    ) -> tuple[Signal, BotOrder | None, PairBalances, str | None] | None:
        '''
        Generates a signal from the strategy and, for BUY/SELL signals, places and confirms
        an order. Returns (signal, placed_order, balances, tick_error), or None if balances
        could not be fetched during error recovery.
        '''
        tick_error: str | None = None
        placed_order: BotOrder | None = None
        balances: PairBalances | None = None
        previous_action = self.strategy.last_action

        try:
            signal = self.strategy.generate_signal(ohlc)['signal']

            if signal in (Signal.BUY, Signal.SELL):
                self.logger.info(f'Signal generated: signal={signal.value}, price={ohlc["close"]}')
                pre_order_balances = self._fetch_balances()
                size = self.position_sizer.calculate_volume(signal, pre_order_balances)
                placed_order = self._submit_order(signal, size)

                if placed_order is None:
                    balances = pre_order_balances
                else:
                    placed_order = self._confirm_order(placed_order)
                    if placed_order.status == OrderStatus.FAILED:
                        self.strategy.last_action = previous_action
                        signal = Signal.HOLD
                        tick_error = f'Order {placed_order.id} failed on exchange'
                        self.logger.warning(tick_error)
                    balances = self._fetch_balances()

            if balances is None:
                balances = self._fetch_balances()

        except Exception as e:
            self.logger.error(f'Error during signal/order flow: {e}', exc_info=True)
            tick_error = str(e)
            if placed_order is None:
                self.strategy.last_action = previous_action
                signal = Signal.HOLD
                self.logger.warning('No order was placed, falling back to HOLD')
            else:
                signal = Signal(placed_order.side.value)
                self.logger.warning(
                    f'Order {placed_order.id} was placed, recording signal as {signal.value}')
            if balances is None:
                try:
                    balances = self._fetch_balances()
                except Exception as balance_error:
                    self.logger.error(
                        f'Failed to fetch balances for error tick: {balance_error}', exc_info=True)
                    return None

        return signal, placed_order, balances, tick_error

    def _submit_order(self, signal: Signal, size: Decimal) -> BotOrder | None:
        '''
        Submits an order to the exchange and persists it to the database.

        :return: Persisted BotOrder, or None in dry-run mode.
        '''
        exchange_order = self.add_order_connector.place(
            self.bot.pair, signal, size, validate=self.dry_run
        )

        if self.dry_run:
            self.logger.info(f'[DRY RUN] Validated order — {exchange_order.order_description}')
            return None

        if not exchange_order.txid:
            raise ValueError(
                'AddOrderResult.txid is missing or empty after live order placement. '
                f'txid={exchange_order.txid}, '
                f'order_description={exchange_order.order_description}'
            )

        exchange_order_id = exchange_order.txid[0]
        order = self.bot_order_repo.add(BotOrder(
            bot_id=self.bot.id,
            run_id=self.run.id,
            exchange_order_id=exchange_order_id,
            side=Side(signal.value),
        ))
        self.logger.info(
            f'Order submitted: txid={exchange_order_id}, side={signal.value}, size={size}')
        return order

    def _persist_results(
            self, ohlc: pd.Series, signal: Signal, balances: PairBalances,
            tick_error: str | None, placed_order: BotOrder | None,
    ) -> None:
        ''' Persists a tick to the database and links any placed order to it. '''
        try:
            tick = self.bot_tick_repo.add(BotTick(
                bot_id=self.bot.id,
                run_id=self.run.id,
                price=Decimal(str(ohlc['close'])),
                signal=signal,
                balance_base=balances.balance_base,
                balance_quote=balances.balance_quote,
                error=tick_error,
            ))
        except Exception as e:
            self.logger.error(f'Failed to persist tick: {e}', exc_info=True)
            return

        if placed_order is not None:
            try:
                self.bot_order_repo.update(replace(placed_order, tick_id=tick.id))
            except Exception as e:
                self.logger.error(
                    f'Failed to link order {placed_order.id} to tick {tick.id}: {e}', exc_info=True)

        if signal == Signal.HOLD:
            self.logger.debug(f'Interval complete: signal={signal.value}')
        else:
            self.logger.info(
                f'Interval complete: signal={signal.value}, '
                f'balance_base={balances.balance_base}, balance_quote={balances.balance_quote}')

    def _confirm_order(self, order: BotOrder) -> BotOrder:
        '''
        Polls the exchange up to 3 times to settle a newly placed order.
        Returns the settled order (FILLED/FAILED), or the original PLACED
        order if still unsettled — to be reconciled next interval.
        '''
        for attempt in range(3):
            if attempt > 0:
                time.sleep(1)

            exchange_order = self.query_orders_connector.fetch([order.exchange_order_id])
            if not exchange_order:
                self.logger.debug(
                    f'Confirm attempt {attempt + 1}/3: no response for order {order.id}')
                continue

            settled = self._settle_order(order, exchange_order[0])
            if settled is not None:
                return settled

            self.logger.debug(
                f'Confirm attempt {attempt + 1}/3: order {order.id} still '
                f'{exchange_order[0].status.value}')

        self.logger.warning(
            f'Order {order.id} still PLACED after 3 attempts; to be reconciled next interval')
        return order
