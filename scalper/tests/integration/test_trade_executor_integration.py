from dataclasses import replace
from decimal import Decimal
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from data_system import Bot, BotOrder, BotRun, BotTick, OrderStatus, Side, Signal
from exchange_connector import OhlcConnector, BalanceConnector, AddOrderConnector, QueryOrdersConnector
from strategy_manager import SmaStrategy, create_strategy
from trade_executor import TradeExecutor
from trade_executor.position_sizer import AllInPositionSizer

PATCH_HEADERS = 'exchange_connector.api.kraken_api_client.get_headers'
MOCK_HEADERS = {'API-Key': 'test', 'API-Sign': 'test'}


@pytest.mark.integration
@pytest.mark.trade_executor_integration
class TestTradeExecutorIntegration:
    '''
    Integration tests for the TradeExecutor.

    These tests verify the full flow from exchange connector stack (connector → service → client)
    through to domain transformation and order lifecycle, mocking only:
    - HTTP boundary (requests.get / requests.post)
    - Auth headers (exchange_connector.api.kraken_api_client.get_headers)
    - Supabase repositories (not the integration boundary being tested)
    - time.sleep (prevent retry delays)

    The exchange connector → service → client stack runs unmocked.
    '''

    # ─── Bot fixture ────────────────────────────────────────────────
    @pytest.fixture
    def bot(self) -> Bot:
        return Bot(
            id='btc_1m_001',
            pair='XXBTZGBP',
            strategy_name='PrecisionTrendStrategy',
            strategy_version='v1.0.0',
            interval=1,
            parameters={},
        )

    # ─── Run fixture ────────────────────────────────────────────────
    @pytest.fixture
    def run(self) -> BotRun:
        return BotRun(bot_id='btc_1m_001')

    # ─── Mock strategy ──────────────────────────────────────────────
    @pytest.fixture
    def mock_strategy(self):
        strategy = Mock()
        strategy.warmup_candles = 50
        strategy.last_action = Signal.SELL
        strategy.generate_signal.return_value = {
            'price': 50000.0,
            'signal': Signal.BUY,
        }
        return strategy

    # ─── Mock repositories ──────────────────────────────────────────
    @pytest.fixture
    def mock_bot_run_repo(self, run):
        repo = Mock()
        repo.add.return_value = run
        return repo

    @pytest.fixture
    def mock_bot_tick_repo(self):
        repo = Mock()
        repo.get_latest_action_by_bot_id.return_value = None

        def add_tick(tick):
            return replace(tick, id=42)

        repo.add.side_effect = add_tick
        return repo

    @pytest.fixture
    def mock_bot_order_repo(self):
        repo = Mock()
        repo.get_placed_by_bot_id.return_value = []
        repo.get_by_tick_id.return_value = None

        def add_order(order):
            return replace(order, id=uuid4())

        repo.add.side_effect = add_order
        return repo

    # ─── Kraken API response fixtures ───────────────────────────────
    @pytest.fixture
    def ohlc_response(self):
        '''Two completed candles + one forming candle (Kraken always appends it).'''
        return {
            'error': [],
            'result': {
                'XXBTZGBP': [
                    [1700000000, '49000.0', '49500.0', '48800.0', '49200.0', '49100.0', '10.5', 200],
                    [1700000060, '49200.0', '49800.0', '49100.0', '49700.0', '49400.0', '12.3', 250],
                    [1700000120, '49700.0', '50100.0', '49600.0', '50000.0', '49800.0', '8.1', 180],
                ],
                'last': 1700000120,
            }
        }

    @pytest.fixture
    def balance_response(self):
        return {
            'error': [],
            'result': {
                'XXBT': '1.5000',
                'ZGBP': '25000.00',
            }
        }

    @pytest.fixture
    def add_order_response(self):
        return {
            'error': [],
            'result': {
                'descr': {'order': 'buy 25000.00 XXBTZGBP @ market'},
                'txid': ['OABCDE-FGHIJ-KLMNOP'],
            }
        }

    @pytest.fixture
    def query_orders_filled_response(self):
        return {
            'error': [],
            'result': {
                'OABCDE-FGHIJ-KLMNOP': {
                    'status': 'closed',
                    'price': '49750.00',
                    'vol_exec': '0.50251256',
                    'fee': '6.45',
                }
            }
        }

    @pytest.fixture
    def query_orders_open_response(self):
        return {
            'error': [],
            'result': {
                'OABCDE-FGHIJ-KLMNOP': {
                    'status': 'open',
                    'price': '0.00',
                    'vol_exec': '0.00',
                    'fee': '0.00',
                }
            }
        }

    @pytest.fixture
    def query_orders_cancelled_response(self):
        return {
            'error': [],
            'result': {
                'OABCDE-FGHIJ-KLMNOP': {
                    'status': 'canceled',
                    'price': '0.00',
                    'vol_exec': '0.00',
                    'fee': '0.00',
                }
            }
        }

    # ─── HTTP mock helper ───────────────────────────────────────────
    def _mock_http_response(self, json_data):
        response = Mock()
        response.json.return_value = json_data
        response.raise_for_status.return_value = None
        return response

    def _build_executor(
            self, bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo, dry_run=False,
    ) -> TradeExecutor:
        '''
        Construct a TradeExecutor with real connectors (sharing a single mocked KrakenApiClient
        pathway) and mock repositories.
        '''
        return TradeExecutor(
            bot=bot,
            strategy=mock_strategy,
            position_sizer=AllInPositionSizer(),
            bot_run_repo=mock_bot_run_repo,
            bot_tick_repo=mock_bot_tick_repo,
            bot_order_repo=mock_bot_order_repo,
            balance_connector=BalanceConnector(),
            ohlc_connector=OhlcConnector(),
            add_order_connector=AddOrderConnector(),
            query_orders_connector=QueryOrdersConnector(),
            dry_run=dry_run,
        )

    # ─── Tests ──────────────────────────────────────────────────────

    def test_buy_signal_full_flow(
            self, bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo, ohlc_response, balance_response,
            add_order_response, query_orders_filled_response,
    ):
        '''
        End-to-end: OHLC fetch → BUY signal → order placement → fill confirmation →
        tick and order persistence. All exchange connectors run through the real
        connector → service → client stack.
        '''
        # Given
        mock_strategy.generate_signal.return_value = {'price': 49700.0, 'signal': Signal.BUY}

        # Track which balance response to return (pre-order vs post-order)
        balance_call_count = [0]
        post_order_balance = {
            'error': [],
            'result': {'XXBT': '2.0025', 'ZGBP': '0.00'},
        }

        def route_request(url, **kwargs):
            if 'OHLC' in url:
                return self._mock_http_response(ohlc_response)
            elif 'Balance' in url:
                balance_call_count[0] += 1
                if balance_call_count[0] <= 1:
                    return self._mock_http_response(balance_response)
                return self._mock_http_response(post_order_balance)
            elif 'AddOrder' in url:
                return self._mock_http_response(add_order_response)
            elif 'QueryOrders' in url:
                return self._mock_http_response(query_orders_filled_response)
            return self._mock_http_response({'error': ['Unknown endpoint'], 'result': {}})

        # Set mark_filled to return the order with updated status
        def mark_filled_side_effect(order_id, price, volume, fee):
            return BotOrder(
                bot_id=bot.id, run_id=mock_bot_run_repo.add.return_value.id,
                exchange_order_id='OABCDE-FGHIJ-KLMNOP', side=Side.BUY,
                status=OrderStatus.FILLED, price=price, volume=volume, fee=fee,
                id=order_id,
            )

        mock_bot_order_repo.mark_filled.side_effect = mark_filled_side_effect

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = self._build_executor(
                bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo, mock_bot_order_repo)

            # When
            executor.execute_interval()

        # Then — tick persisted with correct data
        mock_bot_tick_repo.add.assert_called_once()
        tick_arg = mock_bot_tick_repo.add.call_args[0][0]
        assert isinstance(tick_arg, BotTick)
        assert tick_arg.bot_id == 'btc_1m_001'
        assert tick_arg.signal == Signal.BUY
        assert tick_arg.price == Decimal('49700.0')
        assert tick_arg.error is None

        # Then — post-order balances reflect filled state
        assert tick_arg.balance_base == Decimal('2.0025')
        assert tick_arg.balance_quote == Decimal('0.00')

        # Then — order persisted with exchange_order_id from connector stack
        mock_bot_order_repo.add.assert_called_once()
        order_arg = mock_bot_order_repo.add.call_args[0][0]
        assert isinstance(order_arg, BotOrder)
        assert order_arg.exchange_order_id == 'OABCDE-FGHIJ-KLMNOP'
        assert order_arg.side == Side.BUY
        assert order_arg.status == OrderStatus.PLACED

        # Then — fill confirmed through QueryOrders connector stack
        mock_bot_order_repo.mark_filled.assert_called_once()
        _, fill_kwargs = mock_bot_order_repo.mark_filled.call_args
        if not fill_kwargs:
            fill_args = mock_bot_order_repo.mark_filled.call_args[0]
            assert fill_args[1] == Decimal('49750.00')
            assert fill_args[2] == Decimal('0.50251256')
            assert fill_args[3] == Decimal('6.45')

        # Then — order linked to tick
        mock_bot_order_repo.update.assert_called_once()

    def test_sell_signal_full_flow(
            self, bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo, ohlc_response, balance_response, add_order_response,
            query_orders_filled_response,
    ):
        '''
        End-to-end sell: OHLC fetch → SELL signal → order → fill → persistence.
        Verifies the sell-specific path through the connector stack.
        '''
        # Given
        mock_strategy.last_action = Signal.BUY
        mock_strategy.generate_signal.return_value = {'price': 49700.0, 'signal': Signal.SELL}

        sell_order_response = {
            'error': [],
            'result': {
                'descr': {'order': 'sell 1.5 XXBTZGBP @ market'},
                'txid': ['OSELL-12345-ABCDEF'],
            }
        }
        sell_fill_response = {
            'error': [],
            'result': {
                'OSELL-12345-ABCDEF': {
                    'status': 'closed',
                    'price': '49800.00',
                    'vol_exec': '1.50000000',
                    'fee': '9.72',
                }
            }
        }

        def mark_filled_side_effect(order_id, price, volume, fee):
            return BotOrder(
                bot_id=bot.id, run_id=mock_bot_run_repo.add.return_value.id,
                exchange_order_id='OSELL-12345-ABCDEF', side=Side.SELL,
                status=OrderStatus.FILLED, price=price, volume=volume, fee=fee,
                id=order_id,
            )

        mock_bot_order_repo.mark_filled.side_effect = mark_filled_side_effect

        def route_request(url, **kwargs):
            if 'OHLC' in url:
                return self._mock_http_response(ohlc_response)
            elif 'Balance' in url:
                return self._mock_http_response(balance_response)
            elif 'AddOrder' in url:
                return self._mock_http_response(sell_order_response)
            elif 'QueryOrders' in url:
                return self._mock_http_response(sell_fill_response)
            return self._mock_http_response({'error': ['Unknown'], 'result': {}})

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = self._build_executor(
                bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo, mock_bot_order_repo)

            # When
            executor.execute_interval()

        # Then — order placed as sell
        order_arg = mock_bot_order_repo.add.call_args[0][0]
        assert order_arg.side == Side.SELL
        assert order_arg.exchange_order_id == 'OSELL-12345-ABCDEF'

        # Then — fill details from QueryOrders stack
        fill_args = mock_bot_order_repo.mark_filled.call_args[0]
        assert fill_args[1] == Decimal('49800.00')
        assert fill_args[2] == Decimal('1.50000000')
        assert fill_args[3] == Decimal('9.72')

    def test_hold_signal_no_order_placed(
            self, bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo, ohlc_response, balance_response,
    ):
        '''
        HOLD signal: OHLC fetched through full stack → no order placed → tick persisted.
        '''
        mock_strategy.generate_signal.return_value = {'price': 49700.0, 'signal': Signal.HOLD}

        def route_request(url, **kwargs):
            if 'OHLC' in url:
                return self._mock_http_response(ohlc_response)
            elif 'Balance' in url:
                return self._mock_http_response(balance_response)
            return self._mock_http_response({'error': ['Unknown'], 'result': {}})

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = self._build_executor(
                bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo, mock_bot_order_repo)
            executor.execute_interval()

        # Then — tick persisted with HOLD, no order
        mock_bot_tick_repo.add.assert_called_once()
        assert mock_bot_tick_repo.add.call_args[0][0].signal == Signal.HOLD
        mock_bot_order_repo.add.assert_not_called()

    def test_ohlc_connector_transforms_candles_correctly(
            self, bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo, ohlc_response, balance_response,
    ):
        '''
        Verifies OhlcConnector → OhlcService → KrakenApiClient transforms raw arrays
        into OhlcCandle domain objects, and TradeExecutor extracts the second-to-last
        candle ([-2]) as a pd.Series.
        '''
        mock_strategy.generate_signal.return_value = {'price': 49700.0, 'signal': Signal.HOLD}

        captured_ohlc = []

        def capture_generate(ohlc):
            captured_ohlc.append(ohlc.copy())
            return {'price': ohlc['close'], 'signal': Signal.HOLD}

        mock_strategy.generate_signal.side_effect = capture_generate

        def route_request(url, **kwargs):
            if 'OHLC' in url:
                return self._mock_http_response(ohlc_response)
            elif 'Balance' in url:
                return self._mock_http_response(balance_response)
            return self._mock_http_response({'error': ['Unknown'], 'result': {}})

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = self._build_executor(
                bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo, mock_bot_order_repo)
            executor.execute_interval()

        # Then — strategy received the second-to-last candle (completed, not forming)
        assert len(captured_ohlc) == 1
        ohlc = captured_ohlc[0]
        assert ohlc['open'] == 49200.0
        assert ohlc['high'] == 49800.0
        assert ohlc['low'] == 49100.0
        assert ohlc['close'] == 49700.0

    def test_balance_connector_transforms_to_pair_balances(
            self, bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo, ohlc_response, balance_response,
    ):
        '''
        Verifies BalanceConnector → BalanceService → KrakenApiClient returns raw balance dict,
        and TradeExecutor converts it to Decimal PairBalances using pair symbol lookup.
        '''
        mock_strategy.generate_signal.return_value = {'price': 49700.0, 'signal': Signal.HOLD}

        def route_request(url, **kwargs):
            if 'OHLC' in url:
                return self._mock_http_response(ohlc_response)
            elif 'Balance' in url:
                return self._mock_http_response(balance_response)
            return self._mock_http_response({'error': ['Unknown'], 'result': {}})

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = self._build_executor(
                bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo, mock_bot_order_repo)
            executor.execute_interval()

        tick_arg = mock_bot_tick_repo.add.call_args[0][0]
        assert tick_arg.balance_base == Decimal('1.5000')
        assert tick_arg.balance_quote == Decimal('25000.00')

    def test_position_sizer_receives_correct_balances_for_buy(
            self, bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo, ohlc_response, balance_response,
            add_order_response, query_orders_filled_response,
    ):
        '''
        AllInPositionSizer for BUY should pass the full quote balance as the volume
        to AddOrderConnector, which propagates through the service → client stack.
        '''
        mock_strategy.generate_signal.return_value = {'price': 49700.0, 'signal': Signal.BUY}

        def mark_filled_side_effect(order_id, price, volume, fee):
            return BotOrder(
                bot_id=bot.id, run_id=mock_bot_run_repo.add.return_value.id,
                exchange_order_id='OABCDE-FGHIJ-KLMNOP', side=Side.BUY,
                status=OrderStatus.FILLED, price=price, volume=volume, fee=fee,
                id=order_id,
            )

        mock_bot_order_repo.mark_filled.side_effect = mark_filled_side_effect

        add_order_requests = []

        def route_request(url, **kwargs):
            if 'OHLC' in url:
                return self._mock_http_response(ohlc_response)
            elif 'Balance' in url:
                return self._mock_http_response(balance_response)
            elif 'AddOrder' in url:
                add_order_requests.append(kwargs.get('data', {}))
                return self._mock_http_response(add_order_response)
            elif 'QueryOrders' in url:
                return self._mock_http_response(query_orders_filled_response)
            return self._mock_http_response({'error': ['Unknown'], 'result': {}})

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = self._build_executor(
                bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo, mock_bot_order_repo)
            executor.execute_interval()

        # Then — volume sent to Kraken is the full quote balance (AllInPositionSizer)
        assert len(add_order_requests) == 1
        assert add_order_requests[0]['volume'] == Decimal('25000.00')
        assert add_order_requests[0]['type'] == 'buy'
        assert add_order_requests[0]['pair'] == 'XXBTZGBP'

    def test_order_cancelled_marks_failed_and_rolls_back(
            self, bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo, ohlc_response, balance_response,
            add_order_response, query_orders_cancelled_response,
    ):
        '''
        When QueryOrders returns cancelled (through the full stack), the order is marked
        FAILED and strategy.last_action is rolled back.
        '''
        mock_strategy.generate_signal.return_value = {'price': 49700.0, 'signal': Signal.BUY}
        mock_strategy.last_action = Signal.SELL

        def mark_failed_side_effect(order_id, price, volume, fee):
            return BotOrder(
                bot_id=bot.id, run_id=mock_bot_run_repo.add.return_value.id,
                exchange_order_id='OABCDE-FGHIJ-KLMNOP', side=Side.BUY,
                status=OrderStatus.FAILED, price=price, volume=volume, fee=fee,
                id=order_id,
            )

        mock_bot_order_repo.mark_failed.side_effect = mark_failed_side_effect

        def route_request(url, **kwargs):
            if 'OHLC' in url:
                return self._mock_http_response(ohlc_response)
            elif 'Balance' in url:
                return self._mock_http_response(balance_response)
            elif 'AddOrder' in url:
                return self._mock_http_response(add_order_response)
            elif 'QueryOrders' in url:
                return self._mock_http_response(query_orders_cancelled_response)
            return self._mock_http_response({'error': ['Unknown'], 'result': {}})

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = self._build_executor(
                bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo, mock_bot_order_repo)
            executor.execute_interval()

        # Then — order marked failed through full stack
        mock_bot_order_repo.mark_failed.assert_called_once()
        fill_args = mock_bot_order_repo.mark_failed.call_args[0]
        assert fill_args[1] == Decimal('0.00')

        # Then — strategy last_action rolled back to SELL (BUY order cancelled)
        assert mock_strategy.last_action == Signal.SELL

        # Then — tick persisted with HOLD signal and error
        tick_arg = mock_bot_tick_repo.add.call_args[0][0]
        assert tick_arg.signal == Signal.HOLD
        assert tick_arg.error is not None

    def test_order_still_open_after_retries_stays_placed(
            self, bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo, ohlc_response, balance_response,
            add_order_response, query_orders_open_response,
    ):
        '''
        When QueryOrders returns open for all 3 retry attempts (through the full stack),
        the order stays PLACED — to be reconciled next interval.
        '''
        mock_strategy.generate_signal.return_value = {'price': 49700.0, 'signal': Signal.BUY}

        query_call_count = [0]

        def route_request(url, **kwargs):
            if 'OHLC' in url:
                return self._mock_http_response(ohlc_response)
            elif 'Balance' in url:
                return self._mock_http_response(balance_response)
            elif 'AddOrder' in url:
                return self._mock_http_response(add_order_response)
            elif 'QueryOrders' in url:
                query_call_count[0] += 1
                return self._mock_http_response(query_orders_open_response)
            return self._mock_http_response({'error': ['Unknown'], 'result': {}})

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = self._build_executor(
                bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo, mock_bot_order_repo)
            executor.execute_interval()

        # Then — QueryOrders called 3 times (retry loop)
        assert query_call_count[0] == 3

        # Then — order left as PLACED (mark_filled and mark_failed not called)
        mock_bot_order_repo.mark_filled.assert_not_called()
        mock_bot_order_repo.mark_failed.assert_not_called()

        # Then — tick still persisted with BUY signal (order was placed)
        tick_arg = mock_bot_tick_repo.add.call_args[0][0]
        assert tick_arg.signal == Signal.BUY

    def test_reconciliation_settles_outstanding_order_before_new_interval(
            self, bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo, ohlc_response, balance_response,
    ):
        '''
        At the start of execute_interval, outstanding PLACED orders are reconciled
        through the full QueryOrders connector stack.
        '''
        mock_strategy.generate_signal.return_value = {'price': 49700.0, 'signal': Signal.HOLD}

        outstanding_order = BotOrder(
            bot_id=bot.id, run_id=mock_bot_run_repo.add.return_value.id,
            exchange_order_id='OPREV-ORDER-123456', side=Side.BUY,
            status=OrderStatus.PLACED,
        )
        mock_bot_order_repo.get_placed_by_bot_id.return_value = [outstanding_order]

        reconcile_fill_response = {
            'error': [],
            'result': {
                'OPREV-ORDER-123456': {
                    'status': 'closed',
                    'price': '48500.00',
                    'vol_exec': '0.51546391',
                    'fee': '6.33',
                }
            }
        }

        def mark_filled_side_effect(order_id, price, volume, fee):
            return replace(outstanding_order, status=OrderStatus.FILLED,
                           price=price, volume=volume, fee=fee)

        mock_bot_order_repo.mark_filled.side_effect = mark_filled_side_effect

        def route_request(url, **kwargs):
            if 'OHLC' in url:
                return self._mock_http_response(ohlc_response)
            elif 'Balance' in url:
                return self._mock_http_response(balance_response)
            elif 'QueryOrders' in url:
                return self._mock_http_response(reconcile_fill_response)
            return self._mock_http_response({'error': ['Unknown'], 'result': {}})

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = self._build_executor(
                bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo, mock_bot_order_repo)
            executor.execute_interval()

        # Then — outstanding order reconciled through the full stack
        mock_bot_order_repo.mark_filled.assert_called_once()
        fill_args = mock_bot_order_repo.mark_filled.call_args[0]
        assert fill_args[0] == outstanding_order.id
        assert fill_args[1] == Decimal('48500.00')
        assert fill_args[2] == Decimal('0.51546391')
        assert fill_args[3] == Decimal('6.33')

    def test_dry_run_validates_without_placing(
            self, bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo, ohlc_response, balance_response,
    ):
        '''
        In dry-run mode, the AddOrder request passes `validate=True` through the stack
        and no order is persisted.
        '''
        mock_strategy.generate_signal.return_value = {'price': 49700.0, 'signal': Signal.BUY}

        validate_order_response = {
            'error': [],
            'result': {
                'descr': {'order': 'buy 25000.00 XXBTZGBP @ market'},
            }
        }
        add_order_requests = []

        def route_request(url, **kwargs):
            if 'OHLC' in url:
                return self._mock_http_response(ohlc_response)
            elif 'Balance' in url:
                return self._mock_http_response(balance_response)
            elif 'AddOrder' in url:
                add_order_requests.append(kwargs.get('data', {}))
                return self._mock_http_response(validate_order_response)
            return self._mock_http_response({'error': ['Unknown'], 'result': {}})

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = self._build_executor(
                bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo,
                mock_bot_order_repo, dry_run=True)
            executor.execute_interval()

        # Then — validate=True passed through the stack
        assert len(add_order_requests) == 1
        assert add_order_requests[0]['validate'] is True

        # Then — no order persisted, no tick persisted, no QueryOrders
        mock_bot_order_repo.add.assert_not_called()
        mock_bot_tick_repo.add.assert_not_called()

    def test_warm_up_feeds_history_through_ohlc_stack(
            self, bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo,
    ):
        '''
        warm_up() fetches OHLC history through the full connector stack and feeds
        each candle through generate_signal sequentially.
        '''
        # Given — many candles for warmup
        raw_candles = [
            [1700000000 + i * 60, f'{49000 + i}.0', f'{49500 + i}.0', f'{48800 + i}.0',
             f'{49200 + i}.0', f'{49100 + i}.0', '10.5', 200]
            for i in range(52)  # 51 completed + 1 forming
        ]
        warmup_response = {
            'error': [],
            'result': {
                'XXBTZGBP': raw_candles,
                'last': raw_candles[-1][0],
            }
        }

        mock_strategy.warmup_candles = 50
        signal_calls = []

        def capture_signal(ohlc):
            signal_calls.append(ohlc['close'])
            return {'signal': Signal.HOLD}

        mock_strategy.generate_signal.side_effect = capture_signal

        def route_request(url, **kwargs):
            if 'OHLC' in url:
                return self._mock_http_response(warmup_response)
            return self._mock_http_response({'error': ['Unknown'], 'result': {}})

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = self._build_executor(
                bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo, mock_bot_order_repo)
            executor.warm_up()

        # Then — 51 candles fed (52 minus the forming candle dropped by [:-1])
        assert len(signal_calls) == 51

        # Then — no ticks persisted during warmup
        mock_bot_tick_repo.add.assert_not_called()

    def test_recover_and_execute_end_to_end(
            self, bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo,
    ):
        '''
        Full lifecycle: recover_state → warm_up → execute_interval.
        Verifies state recovery flows correctly into signal generation.
        '''
        # Given — previous BUY tick exists
        previous_tick = BotTick(
            bot_id=bot.id, run_id=uuid4(),
            price=Decimal('48000.00'), signal=Signal.BUY,
            balance_base=Decimal('1.0'), balance_quote=Decimal('0.0'),
            id=10,
        )
        mock_bot_tick_repo.get_latest_action_by_bot_id.return_value = previous_tick
        mock_bot_order_repo.get_by_tick_id.return_value = None

        warmup_candles = [
            [1700000000 + i * 60, f'{49000 + i}.0', f'{49500 + i}.0', f'{48800 + i}.0',
             f'{49200 + i}.0', f'{49100 + i}.0', '10.5', 200]
            for i in range(12)  # 11 completed + 1 forming
        ]
        warmup_response = {
            'error': [],
            'result': {
                'XXBTZGBP': warmup_candles,
                'last': warmup_candles[-1][0],
            }
        }
        mock_strategy.warmup_candles = 10

        # generate_signal: first 11 calls are warmup, last call is execute_interval
        signal_counter = [0]

        def signal_side_effect(ohlc):
            signal_counter[0] += 1
            return {'price': ohlc['close'], 'signal': Signal.HOLD}

        mock_strategy.generate_signal.side_effect = signal_side_effect

        balance_response = {
            'error': [],
            'result': {'XXBT': '1.5000', 'ZGBP': '25000.00'},
        }
        ohlc_call_count = [0]
        interval_ohlc_response = {
            'error': [],
            'result': {
                'XXBTZGBP': [
                    [1700000000, '49000.0', '49500.0', '48800.0', '49200.0', '49100.0', '10.5', 200],
                    [1700000060, '49200.0', '49800.0', '49100.0', '49700.0', '49400.0', '12.3', 250],
                    [1700000120, '49700.0', '50100.0', '49600.0', '50000.0', '49800.0', '8.1', 180],
                ],
                'last': 1700000120,
            }
        }

        def route_request(url, **kwargs):
            if 'OHLC' in url:
                ohlc_call_count[0] += 1
                if ohlc_call_count[0] == 1:
                    return self._mock_http_response(warmup_response)
                return self._mock_http_response(interval_ohlc_response)
            elif 'Balance' in url:
                return self._mock_http_response(balance_response)
            return self._mock_http_response({'error': ['Unknown'], 'result': {}})

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = self._build_executor(
                bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo, mock_bot_order_repo)

            # When
            executor.recover_state()
            executor.warm_up()
            executor.execute_interval()

        # Then — state recovered from previous tick
        assert mock_strategy.last_action == Signal.BUY

        # Then — warmup + interval signal calls all went through
        assert signal_counter[0] == 12  # 11 warmup + 1 interval

        # Then — tick persisted for interval (not warmup)
        mock_bot_tick_repo.add.assert_called_once()

    def test_kraken_api_error_propagates_through_stack(
            self, bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo,
    ):
        '''
        A Kraken API error during OHLC fetch propagates through the full
        client → service → connector stack, causing the interval to skip.
        '''
        error_response = {
            'error': ['EQuery:Unknown asset pair'],
            'result': {},
        }

        def route_request(url, **kwargs):
            return self._mock_http_response(error_response)

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = self._build_executor(
                bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo, mock_bot_order_repo)
            executor.execute_interval()

        # Then — no tick or order persisted (OHLC failure = skip)
        mock_bot_tick_repo.add.assert_not_called()
        mock_bot_order_repo.add.assert_not_called()

    def test_multiple_placed_orders_reconciled_in_single_batch(
            self, bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo, ohlc_response, balance_response,
    ):
        '''
        Multiple outstanding PLACED orders are sent to QueryOrders in a single
        comma-separated request (single API call) and reconciled individually.
        '''
        mock_strategy.generate_signal.return_value = {'price': 49700.0, 'signal': Signal.HOLD}

        order1 = BotOrder(
            bot_id=bot.id, run_id=mock_bot_run_repo.add.return_value.id,
            exchange_order_id='ORDER-AAA-111111', side=Side.BUY,
            status=OrderStatus.PLACED,
        )
        order2 = BotOrder(
            bot_id=bot.id, run_id=mock_bot_run_repo.add.return_value.id,
            exchange_order_id='ORDER-BBB-222222', side=Side.SELL,
            status=OrderStatus.PLACED,
        )
        mock_bot_order_repo.get_placed_by_bot_id.return_value = [order1, order2]

        batch_response = {
            'error': [],
            'result': {
                'ORDER-AAA-111111': {
                    'status': 'closed',
                    'price': '48500.00',
                    'vol_exec': '0.50000000',
                    'fee': '6.00',
                },
                'ORDER-BBB-222222': {
                    'status': 'canceled',
                    'price': '0.00',
                    'vol_exec': '0.00',
                    'fee': '0.00',
                },
            }
        }

        def mark_filled_side_effect(order_id, price, volume, fee):
            return replace(order1, status=OrderStatus.FILLED,
                           price=price, volume=volume, fee=fee)

        def mark_failed_side_effect(order_id, price, volume, fee):
            return replace(order2, status=OrderStatus.FAILED,
                           price=price, volume=volume, fee=fee)

        mock_bot_order_repo.mark_filled.side_effect = mark_filled_side_effect
        mock_bot_order_repo.mark_failed.side_effect = mark_failed_side_effect

        query_requests = []

        def route_request(url, **kwargs):
            if 'OHLC' in url:
                return self._mock_http_response(ohlc_response)
            elif 'Balance' in url:
                return self._mock_http_response(balance_response)
            elif 'QueryOrders' in url:
                query_requests.append(kwargs.get('data', {}))
                return self._mock_http_response(batch_response)
            return self._mock_http_response({'error': ['Unknown'], 'result': {}})

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = self._build_executor(
                bot, mock_strategy, mock_bot_run_repo, mock_bot_tick_repo, mock_bot_order_repo)
            executor.execute_interval()

        # Then — single QueryOrders call with comma-separated txids
        assert len(query_requests) == 1
        txid_param = query_requests[0]['txid']
        assert 'ORDER-AAA-111111' in txid_param
        assert 'ORDER-BBB-222222' in txid_param

        # Then — one filled, one failed
        mock_bot_order_repo.mark_filled.assert_called_once()
        mock_bot_order_repo.mark_failed.assert_called_once()


@pytest.mark.integration
@pytest.mark.trade_executor_integration
class TestTradeExecutorRealStrategyIntegration:
    '''
    Integration tests using a real SmaStrategy with actual indicators and rules.

    Uses SmaStrategy(short_window=3, long_window=5) with deterministic price data
    to verify the full pipeline: OHLC connector stack → real strategy indicators →
    real crossover rule → order placement → persistence.
    '''

    @pytest.fixture
    def bot(self) -> Bot:
        return Bot(
            id='btc_1m_001',
            pair='XXBTZGBP',
            strategy_name='SmaStrategy',
            strategy_version='v1.0.0',
            interval=1,
            parameters={'short_window': 3, 'long_window': 5},
        )

    @pytest.fixture
    def strategy(self, bot) -> SmaStrategy:
        return create_strategy(bot.strategy_name, bot.parameters)

    @pytest.fixture
    def run(self) -> BotRun:
        return BotRun(bot_id='btc_1m_001')

    @pytest.fixture
    def mock_bot_run_repo(self, run):
        repo = Mock()
        repo.add.return_value = run
        return repo

    @pytest.fixture
    def mock_bot_tick_repo(self):
        repo = Mock()
        repo.get_latest_action_by_bot_id.return_value = None

        def add_tick(tick):
            return replace(tick, id=42)

        repo.add.side_effect = add_tick
        return repo

    @pytest.fixture
    def mock_bot_order_repo(self):
        repo = Mock()
        repo.get_placed_by_bot_id.return_value = []
        repo.get_by_tick_id.return_value = None

        def add_order(order):
            return replace(order, id=uuid4())

        repo.add.side_effect = add_order
        return repo

    @pytest.fixture
    def balance_response(self):
        return {
            'error': [],
            'result': {'XXBT': '0.00', 'ZGBP': '25000.00'},
        }

    @pytest.fixture
    def add_order_response(self):
        return {
            'error': [],
            'result': {
                'descr': {'order': 'buy 25000.00 XXBTZGBP @ market'},
                'txid': ['OREAL-STRAT-BUYSIG'],
            }
        }

    @pytest.fixture
    def query_orders_filled_response(self):
        return {
            'error': [],
            'result': {
                'OREAL-STRAT-BUYSIG': {
                    'status': 'closed',
                    'price': '50100.00',
                    'vol_exec': '0.49900199',
                    'fee': '6.50',
                }
            }
        }

    def _mock_http_response(self, json_data):
        response = Mock()
        response.json.return_value = json_data
        response.raise_for_status.return_value = None
        return response

    def _build_ohlc_response(self, prices: list[float], base_timestamp: int = 1700000000) -> dict:
        '''
        Build a Kraken OHLC API response from a list of close prices.

        Each candle has open=high=low=close for simplicity — SMA only uses close.
        '''
        candles = [
            [base_timestamp + i * 60, str(p), str(p), str(p), str(p), str(p), '10.0', 100]
            for i, p in enumerate(prices)
        ]
        return {
            'error': [],
            'result': {
                'XXBTZGBP': candles,
                'last': candles[-1][0],
            }
        }

    def test_warmup_and_buy_signal_with_real_strategy(
            self, bot, strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo, balance_response, add_order_response,
            query_orders_filled_response,
    ):
        '''
        Full pipeline with real SmaStrategy(short=3, long=5):

        Warmup prices: [100, 100, 100, 100, 100, 100, 100]
          → After warmup: short_sma=100, long_sma=100 (no crossover, all HOLD)
          → last_action stays at SELL (default)

        Interval candle: close=120 (sharp spike)
          → short_sma(3): mean of [100, 100, 120] = 106.67
          → long_sma(5): mean of [100, 100, 100, 100, 120] = 104.0
          → Previous: short_sma <= long_sma (both 100), now short > long → golden cross → BUY

        Verifies the real indicator math + crossover rule produces a BUY that flows through
        order placement and persistence.
        '''
        # Given — flat warmup prices, then a spike to trigger golden cross
        warmup_prices = [100.0] * 7  # 6 completed + 1 forming (dropped by [:-1])
        interval_prices = [100.0, 120.0, 120.0]  # [-2] is the completed candle = 120

        warmup_ohlc = self._build_ohlc_response(warmup_prices)
        interval_ohlc = self._build_ohlc_response(interval_prices, base_timestamp=1700001000)

        def mark_filled_side_effect(order_id, price, volume, fee):
            return BotOrder(
                bot_id=bot.id, run_id=mock_bot_run_repo.add.return_value.id,
                exchange_order_id='OREAL-STRAT-BUYSIG', side=Side.BUY,
                status=OrderStatus.FILLED, price=price, volume=volume, fee=fee,
                id=order_id,
            )

        mock_bot_order_repo.mark_filled.side_effect = mark_filled_side_effect

        ohlc_call_count = [0]

        def route_request(url, **kwargs):
            if 'OHLC' in url:
                ohlc_call_count[0] += 1
                if ohlc_call_count[0] == 1:
                    return self._mock_http_response(warmup_ohlc)
                return self._mock_http_response(interval_ohlc)
            elif 'Balance' in url:
                return self._mock_http_response(balance_response)
            elif 'AddOrder' in url:
                return self._mock_http_response(add_order_response)
            elif 'QueryOrders' in url:
                return self._mock_http_response(query_orders_filled_response)
            return self._mock_http_response({'error': ['Unknown'], 'result': {}})

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = TradeExecutor(
                bot=bot, strategy=strategy, position_sizer=AllInPositionSizer(),
                bot_run_repo=mock_bot_run_repo, bot_tick_repo=mock_bot_tick_repo,
                bot_order_repo=mock_bot_order_repo, balance_connector=BalanceConnector(),
                ohlc_connector=OhlcConnector(), add_order_connector=AddOrderConnector(),
                query_orders_connector=QueryOrdersConnector(),
            )

            executor.warm_up()
            executor.execute_interval()

        # Then — real strategy produced BUY from golden cross
        tick_arg = mock_bot_tick_repo.add.call_args[0][0]
        assert tick_arg.signal == Signal.BUY

        # Then — order placed and filled
        mock_bot_order_repo.add.assert_called_once()
        order_arg = mock_bot_order_repo.add.call_args[0][0]
        assert order_arg.side == Side.BUY
        mock_bot_order_repo.mark_filled.assert_called_once()

        # Then — strategy state updated
        assert strategy.last_action == Signal.BUY

    def test_warmup_hold_when_no_crossover(
            self, bot, strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo, balance_response,
    ):
        '''
        Warmup with flat prices, then interval with same flat price → no crossover → HOLD.
        Verifies that real indicators correctly produce no signal when there is no trend change.
        '''
        warmup_prices = [100.0] * 7
        interval_prices = [100.0, 100.0, 100.0]  # No change → no crossover

        warmup_ohlc = self._build_ohlc_response(warmup_prices)
        interval_ohlc = self._build_ohlc_response(interval_prices, base_timestamp=1700001000)

        ohlc_call_count = [0]

        def route_request(url, **kwargs):
            if 'OHLC' in url:
                ohlc_call_count[0] += 1
                if ohlc_call_count[0] == 1:
                    return self._mock_http_response(warmup_ohlc)
                return self._mock_http_response(interval_ohlc)
            elif 'Balance' in url:
                return self._mock_http_response(balance_response)
            return self._mock_http_response({'error': ['Unknown'], 'result': {}})

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = TradeExecutor(
                bot=bot, strategy=strategy, position_sizer=AllInPositionSizer(),
                bot_run_repo=mock_bot_run_repo, bot_tick_repo=mock_bot_tick_repo,
                bot_order_repo=mock_bot_order_repo, balance_connector=BalanceConnector(),
                ohlc_connector=OhlcConnector(), add_order_connector=AddOrderConnector(),
                query_orders_connector=QueryOrdersConnector(),
            )

            executor.warm_up()
            executor.execute_interval()

        # Then — HOLD, no order placed
        tick_arg = mock_bot_tick_repo.add.call_args[0][0]
        assert tick_arg.signal == Signal.HOLD
        mock_bot_order_repo.add.assert_not_called()

    def test_recover_state_then_suppress_duplicate_signal(
            self, bot, strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo, balance_response,
    ):
        '''
        Recover last_action=BUY from a previous tick, then feed prices that would
        produce another BUY crossover. The real strategy's consecutive-signal suppression
        should convert it to HOLD.
        '''
        # Given — recover from a previous BUY
        previous_tick = BotTick(
            bot_id=bot.id, run_id=uuid4(),
            price=Decimal('50000.00'), signal=Signal.BUY,
            balance_base=Decimal('1.0'), balance_quote=Decimal('0.0'),
            id=10,
        )
        mock_bot_tick_repo.get_latest_action_by_bot_id.return_value = previous_tick
        mock_bot_order_repo.get_by_tick_id.return_value = None

        # Warmup: trending up, so short > long at the end (already in BUY territory)
        warmup_prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0]
        # Interval: continued uptrend — short still > long, but it was already above
        # so there's no *new* crossover. Even if there were, last_action=BUY suppresses it.
        interval_prices = [106.0, 107.0, 107.0]

        warmup_ohlc = self._build_ohlc_response(warmup_prices)
        interval_ohlc = self._build_ohlc_response(interval_prices, base_timestamp=1700001000)

        ohlc_call_count = [0]

        def route_request(url, **kwargs):
            if 'OHLC' in url:
                ohlc_call_count[0] += 1
                if ohlc_call_count[0] == 1:
                    return self._mock_http_response(warmup_ohlc)
                return self._mock_http_response(interval_ohlc)
            elif 'Balance' in url:
                return self._mock_http_response(balance_response)
            return self._mock_http_response({'error': ['Unknown'], 'result': {}})

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = TradeExecutor(
                bot=bot, strategy=strategy, position_sizer=AllInPositionSizer(),
                bot_run_repo=mock_bot_run_repo, bot_tick_repo=mock_bot_tick_repo,
                bot_order_repo=mock_bot_order_repo, balance_connector=BalanceConnector(),
                ohlc_connector=OhlcConnector(), add_order_connector=AddOrderConnector(),
                query_orders_connector=QueryOrdersConnector(),
            )

            executor.recover_state()
            executor.warm_up()
            executor.execute_interval()

        # Then — last_action=BUY recovered
        assert strategy.last_action == Signal.BUY

        # Then — HOLD (no new crossover, or suppressed duplicate)
        tick_arg = mock_bot_tick_repo.add.call_args[0][0]
        assert tick_arg.signal == Signal.HOLD
        mock_bot_order_repo.add.assert_not_called()

    def test_sell_signal_after_buy_with_real_strategy(
            self, bot, strategy, mock_bot_run_repo, mock_bot_tick_repo,
            mock_bot_order_repo, balance_response,
    ):
        '''
        Warmup establishes a BUY crossover, then interval price drops to trigger
        a death cross → SELL signal through the real strategy.

        SMA(short=3, long=5). Warmup: 8 completed candles after [:-1].

        Warmup candle history (close prices):
          [100, 100, 100, 100, 100, 106, 106, 106]
          After candle 5 (100): short=100.0, long=100.0 → first both-populated
          After candle 6 (106): short=102.0, long=101.2 → cross above → BUY
          After candle 7 (106): short=104.0, long=102.4 → still above → HOLD
          After candle 8 (106): short=106.0, long=103.6 → still above → HOLD
          last_action = BUY after warmup

        Interval candle close=80:
          short(3): [106, 106, 80] → 97.33
          long(5): [100, 106, 106, 106, 80] → 99.6
          prev: short(106.0) >= long(103.6), now short(97.33) < long(99.6) → death cross → SELL
        '''
        # Warmup: 9 total (8 completed + 1 forming dropped by [:-1])
        warmup_prices = [100.0, 100.0, 100.0, 100.0, 100.0, 106.0, 106.0, 106.0, 999.0]
        interval_prices = [999.0, 80.0, 80.0]  # [-2] = 80.0

        warmup_ohlc = self._build_ohlc_response(warmup_prices)
        interval_ohlc = self._build_ohlc_response(interval_prices, base_timestamp=1700001000)

        sell_order_response = {
            'error': [],
            'result': {
                'descr': {'order': 'sell 1.5 XXBTZGBP @ market'},
                'txid': ['OREAL-STRAT-SELLSIG'],
            }
        }
        sell_fill_response = {
            'error': [],
            'result': {
                'OREAL-STRAT-SELLSIG': {
                    'status': 'closed',
                    'price': '70.00',
                    'vol_exec': '1.50000000',
                    'fee': '0.05',
                }
            }
        }

        post_sell_balance = {
            'error': [],
            'result': {'XXBT': '0.00', 'ZGBP': '104.95'},
        }

        def mark_filled_side_effect(order_id, price, volume, fee):
            return BotOrder(
                bot_id=bot.id, run_id=mock_bot_run_repo.add.return_value.id,
                exchange_order_id='OREAL-STRAT-SELLSIG', side=Side.SELL,
                status=OrderStatus.FILLED, price=price, volume=volume, fee=fee,
                id=order_id,
            )

        mock_bot_order_repo.mark_filled.side_effect = mark_filled_side_effect

        ohlc_call_count = [0]
        balance_call_count = [0]

        def route_request(url, **kwargs):
            nonlocal ohlc_call_count, balance_call_count
            if 'OHLC' in url:
                ohlc_call_count[0] += 1
                if ohlc_call_count[0] == 1:
                    return self._mock_http_response(warmup_ohlc)
                return self._mock_http_response(interval_ohlc)
            elif 'Balance' in url:
                balance_call_count[0] += 1
                if balance_call_count[0] <= 1:
                    return self._mock_http_response(balance_response)
                return self._mock_http_response(post_sell_balance)
            elif 'AddOrder' in url:
                return self._mock_http_response(sell_order_response)
            elif 'QueryOrders' in url:
                return self._mock_http_response(sell_fill_response)
            return self._mock_http_response({'error': ['Unknown'], 'result': {}})

        with (
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.get', side_effect=route_request),
            patch('requests.post', side_effect=lambda url, **kwargs: route_request(url, **kwargs)),
            patch('time.sleep'),
        ):
            executor = TradeExecutor(
                bot=bot, strategy=strategy, position_sizer=AllInPositionSizer(),
                bot_run_repo=mock_bot_run_repo, bot_tick_repo=mock_bot_tick_repo,
                bot_order_repo=mock_bot_order_repo, balance_connector=BalanceConnector(),
                ohlc_connector=OhlcConnector(), add_order_connector=AddOrderConnector(),
                query_orders_connector=QueryOrdersConnector(),
            )

            executor.warm_up()
            executor.execute_interval()

        # Then — real strategy produced SELL from death cross
        tick_arg = mock_bot_tick_repo.add.call_args[0][0]
        assert tick_arg.signal == Signal.SELL
        assert strategy.last_action == Signal.SELL

        # Then — order placed as sell and filled
        order_arg = mock_bot_order_repo.add.call_args[0][0]
        assert order_arg.side == Side.SELL
        mock_bot_order_repo.mark_filled.assert_called_once()
