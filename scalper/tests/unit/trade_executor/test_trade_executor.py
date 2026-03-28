import logging
from decimal import Decimal
from unittest.mock import Mock, patch
from uuid import uuid4

import pandas as pd
import pytest

from data_system.models.bot_model import Bot
from data_system.models.bot_order_model import BotOrder, Side
from data_system.models.bot_run_model import BotRun
from data_system.models.bot_tick_model import Signal
from data_system.repositories.bot_order.bot_order_repository import BotOrderRepository
from data_system.repositories.bot_run.bot_run_repository import BotRunRepository
from data_system.repositories.bot_tick.bot_tick_repository import BotTickRepository
from exchange_connector.connectors.add_order_connector import AddOrderConnector
from exchange_connector.connectors.balance_connector import BalanceConnector
from exchange_connector.connectors.ohlc_connector import OhlcConnector
from exchange_connector.connectors.query_orders_connector import QueryOrdersConnector
from exchange_connector.models.ohlc_candle import OhlcCandle
from exchange_connector.models.query_order_result import QueryOrderResult, QueryOrderStatus
from strategy_manager.strategies.base_strategy import Strategy
from trade_executor.position_sizer import PairBalances, PositionSizer
from trade_executor.trade_executor import BotLoggerAdapter, TradeExecutor
from utils.pair_config import PairSymbols


@pytest.mark.trade_executor
class TestBotLoggerAdapter:
    def test_process_prefixes_bot_id_to_message(self):
        adapter = BotLoggerAdapter(logging.getLogger(__name__), {'bot_id': 'btc_1m_001'})

        result_msg, _ = adapter.process('some message', {})

        assert result_msg == '[btc_1m_001] some message'

    def test_process_preserves_kwargs(self):
        adapter = BotLoggerAdapter(logging.getLogger(__name__), {'bot_id': 'btc_1m_001'})
        kwargs = {'exc_info': True}

        _, result_kwargs = adapter.process('msg', kwargs)

        assert result_kwargs == {'exc_info': True}


@pytest.mark.trade_executor
class TestTradeExecutor:
    @pytest.fixture
    def bot(self) -> Bot:
        return Bot(
            id='btc_1m_001',
            pair='XXBTZGBP',
            strategy_name='PrecisionTrendStrategy',
            strategy_version='v1.0.0',
            interval=1,
            parameters={'short_ema': 43},
        )

    @pytest.fixture
    def mock_strategy(self):
        return Mock(spec=Strategy)

    @pytest.fixture
    def mock_position_sizer(self):
        return Mock(spec=PositionSizer)

    @pytest.fixture
    def mock_bot_run_repo(self, bot) -> Mock:
        repo = Mock(spec=BotRunRepository)
        repo.add.return_value = BotRun(bot_id=bot.id)
        return repo

    @pytest.fixture
    def mock_bot_tick_repo(self) -> Mock:
        return Mock(spec=BotTickRepository)

    @pytest.fixture
    def mock_bot_order_repo(self) -> Mock:
        return Mock(spec=BotOrderRepository)

    @pytest.fixture
    def mock_balance_connector(self) -> Mock:
        return Mock(spec=BalanceConnector)

    @pytest.fixture
    def mock_ohlc_connector(self) -> Mock:
        return Mock(spec=OhlcConnector)

    @pytest.fixture
    def mock_add_order_connector(self) -> Mock:
        return Mock(spec=AddOrderConnector)

    @pytest.fixture
    def mock_query_orders_connector(self) -> Mock:
        return Mock(spec=QueryOrdersConnector)

    @pytest.fixture
    def executor(
            self, bot, mock_strategy, mock_position_sizer, mock_bot_run_repo,
            mock_bot_tick_repo, mock_bot_order_repo, mock_balance_connector,
            mock_ohlc_connector, mock_add_order_connector, mock_query_orders_connector,
    ) -> TradeExecutor:
        return TradeExecutor(
            bot=bot,
            strategy=mock_strategy,
            position_sizer=mock_position_sizer,
            bot_run_repo=mock_bot_run_repo,
            bot_tick_repo=mock_bot_tick_repo,
            bot_order_repo=mock_bot_order_repo,
            balance_connector=mock_balance_connector,
            ohlc_connector=mock_ohlc_connector,
            add_order_connector=mock_add_order_connector,
            query_orders_connector=mock_query_orders_connector,
        )

    # --- Constructor ---

    def test_constructor_stores_bot(self, executor, bot):
        assert executor.bot is bot

    def test_constructor_stores_strategy(self, executor, mock_strategy):
        assert executor.strategy is mock_strategy

    def test_constructor_stores_position_sizer(self, executor, mock_position_sizer):
        assert executor.position_sizer is mock_position_sizer

    def test_constructor_stores_repositories(
            self, executor, mock_bot_run_repo, mock_bot_tick_repo, mock_bot_order_repo,
    ):
        assert executor.bot_run_repo is mock_bot_run_repo
        assert executor.bot_tick_repo is mock_bot_tick_repo
        assert executor.bot_order_repo is mock_bot_order_repo

    def test_constructor_stores_connectors(
            self, executor, mock_balance_connector, mock_ohlc_connector,
            mock_add_order_connector, mock_query_orders_connector,
    ):
        assert executor.balance_connector is mock_balance_connector
        assert executor.ohlc_connector is mock_ohlc_connector
        assert executor.add_order_connector is mock_add_order_connector
        assert executor.query_orders_connector is mock_query_orders_connector

    def test_constructor_dry_run_defaults_to_false(self, executor):
        assert executor.dry_run is False

    # --- warm_up ---

    def test_warm_up_calls_generate_signal_for_each_candle(self, executor, mock_strategy):
        candles = [
            pd.Series({'open': 1.0, 'high': 2.0, 'low': 0.5, 'close': 1.5}),
            pd.Series({'open': 1.5, 'high': 2.5, 'low': 1.0, 'close': 2.0}),
            pd.Series({'open': 2.0, 'high': 3.0, 'low': 1.5, 'close': 2.5}),
        ]
        mock_strategy.warmup_candles = 3
        executor._fetch_ohlc_history = Mock(return_value=candles)

        executor.warm_up()

        assert mock_strategy.generate_signal.call_count == 3

    def test_warm_up_passes_each_ohlc_series_to_generate_signal(self, executor, mock_strategy):
        candles = [
            pd.Series({'open': 1.0, 'high': 2.0, 'low': 0.5, 'close': 1.5}),
            pd.Series({'open': 1.5, 'high': 2.5, 'low': 1.0, 'close': 2.0}),
        ]
        mock_strategy.warmup_candles = 2
        executor._fetch_ohlc_history = Mock(return_value=candles)

        executor.warm_up()

        calls = mock_strategy.generate_signal.call_args_list
        pd.testing.assert_series_equal(calls[0].args[0], candles[0])
        pd.testing.assert_series_equal(calls[1].args[0], candles[1])

    def test_warm_up_with_empty_history_does_not_call_generate_signal(self, executor, mock_strategy):
        mock_strategy.warmup_candles = 3
        executor._fetch_ohlc_history = Mock(return_value=[])

        executor.warm_up()

        mock_strategy.generate_signal.assert_not_called()

    def test_warm_up_warns_when_fewer_candles_than_required(self, executor, mock_strategy):
        candles = [
            pd.Series({'open': 1.0, 'high': 2.0, 'low': 0.5, 'close': 1.5}),
            pd.Series({'open': 1.5, 'high': 2.5, 'low': 1.0, 'close': 2.0}),
        ]
        mock_strategy.warmup_candles = 5
        executor._fetch_ohlc_history = Mock(return_value=candles)
        executor.logger = Mock()

        executor.warm_up()

        executor.logger.warning.assert_called_once()

    def test_warm_up_does_not_warn_when_sufficient_candles(self, executor, mock_strategy):
        candles = [
            pd.Series({'open': 1.0, 'high': 2.0, 'low': 0.5, 'close': 1.5}),
            pd.Series({'open': 1.5, 'high': 2.5, 'low': 1.0, 'close': 2.0}),
            pd.Series({'open': 2.0, 'high': 3.0, 'low': 1.5, 'close': 2.5}),
        ]
        mock_strategy.warmup_candles = 3
        executor._fetch_ohlc_history = Mock(return_value=candles)
        executor.logger = Mock()

        executor.warm_up()

        executor.logger.warning.assert_not_called()

    def test_warm_up_logs_completion_with_candle_count(self, executor, mock_strategy):
        candles = [
            pd.Series({'open': 1.0, 'high': 2.0, 'low': 0.5, 'close': 1.5}),
            pd.Series({'open': 1.5, 'high': 2.5, 'low': 1.0, 'close': 2.0}),
        ]
        mock_strategy.warmup_candles = 2
        executor._fetch_ohlc_history = Mock(return_value=candles)
        executor.logger = Mock()

        executor.warm_up()

        info_messages = [str(call.args[0]) for call in executor.logger.info.call_args_list]
        assert any('2 candles' in msg for msg in info_messages)

    def test_constructor_stores_dry_run_true_when_set(
            self, bot, mock_strategy, mock_position_sizer, mock_bot_run_repo,
            mock_bot_tick_repo, mock_bot_order_repo, mock_balance_connector,
            mock_ohlc_connector, mock_add_order_connector, mock_query_orders_connector,
    ):
        executor = TradeExecutor(
            bot=bot,
            strategy=mock_strategy,
            position_sizer=mock_position_sizer,
            bot_run_repo=mock_bot_run_repo,
            bot_tick_repo=mock_bot_tick_repo,
            bot_order_repo=mock_bot_order_repo,
            balance_connector=mock_balance_connector,
            ohlc_connector=mock_ohlc_connector,
            add_order_connector=mock_add_order_connector,
            query_orders_connector=mock_query_orders_connector,
            dry_run=True,
        )

        assert executor.dry_run is True

    def test_constructor_sets_shutting_down_false(self, executor):
        assert executor._shutting_down is False

    def test_constructor_resolves_pair_symbols(self, executor):
        assert executor.pair_symbols == PairSymbols(base='XXBT', quote='ZGBP')

    def test_constructor_creates_bot_run_with_correct_bot_id(self, executor, bot, mock_bot_run_repo):
        call_args = mock_bot_run_repo.add.call_args[0][0]
        assert isinstance(call_args, BotRun)
        assert call_args.bot_id == bot.id

    def test_constructor_stores_persisted_run(self, executor, mock_bot_run_repo):
        assert executor.run is mock_bot_run_repo.add.return_value

    def test_constructor_configures_logger_with_bot_id(self, executor, bot):
        assert isinstance(executor.logger, BotLoggerAdapter)
        assert executor.logger.extra['bot_id'] == bot.id

    # --- request_shutdown ---

    def test_request_shutdown_sets_shutting_down_true(self, executor):
        executor.request_shutdown()
        assert executor._shutting_down is True

    def test_request_shutdown_logs_message(self, executor):
        executor.logger = Mock()
        executor.request_shutdown()
        executor.logger.info.assert_called_once_with('Shutdown requested')

    # --- _fetch_ohlc ---

    @pytest.fixture
    def sample_candles(self) -> list[OhlcCandle]:
        def _make_candle(close: float) -> OhlcCandle:
            return OhlcCandle(
                timestamp=1700000000,
                open=close - 10.0,
                high=close + 5.0,
                low=close - 15.0,
                close=close,
                vwap=close,
                volume=100.0,
                count=50,
            )
        # Three candles: index -2 is the completed candle we want, -1 is the forming candle.
        return [_make_candle(49900.0), _make_candle(50000.0), _make_candle(50100.0)]

    def test_fetch_ohlc_calls_connector_with_correct_pair_and_interval(self, executor, mock_ohlc_connector, sample_candles):
        mock_ohlc_connector.fetch.return_value = sample_candles

        with patch('time.time', return_value=1700000120.0):
            executor._fetch_ohlc()

        mock_ohlc_connector.fetch.assert_called_once()
        args = mock_ohlc_connector.fetch.call_args[0]
        assert args[0] == 'XXBTZGBP'
        assert args[1] == 1

    def test_fetch_ohlc_calls_connector_with_since_two_intervals_ago(self, executor, mock_ohlc_connector, sample_candles):
        # bot.interval is 1 minute; two intervals back = 1 * 60 * 2 = 120 seconds
        mock_ohlc_connector.fetch.return_value = sample_candles
        frozen_time = 1700000120.0

        with patch('time.time', return_value=frozen_time):
            executor._fetch_ohlc()

        expected_since = int(frozen_time) - 1 * 60 * 2
        args = mock_ohlc_connector.fetch.call_args[0]
        assert args[2] == expected_since

    def test_fetch_ohlc_returns_series_from_second_to_last_candle(self, executor, mock_ohlc_connector, sample_candles):
        mock_ohlc_connector.fetch.return_value = sample_candles
        completed_candle = sample_candles[-2]

        with patch('time.time', return_value=1700000120.0):
            result = executor._fetch_ohlc()

        assert result['open'] == completed_candle.open
        assert result['high'] == completed_candle.high
        assert result['low'] == completed_candle.low
        assert result['close'] == completed_candle.close

    def test_fetch_ohlc_returns_pandas_series(self, executor, mock_ohlc_connector, sample_candles):
        mock_ohlc_connector.fetch.return_value = sample_candles

        with patch('time.time', return_value=1700000120.0):
            result = executor._fetch_ohlc()

        assert isinstance(result, pd.Series)

    def test_fetch_ohlc_series_contains_only_ohlc_keys(self, executor, mock_ohlc_connector, sample_candles):
        mock_ohlc_connector.fetch.return_value = sample_candles

        with patch('time.time', return_value=1700000120.0):
            result = executor._fetch_ohlc()

        assert list(result.index) == ['open', 'high', 'low', 'close']

    # --- _fetch_ohlc_history ---

    def test_fetch_ohlc_history_calls_connector_with_correct_pair_and_interval(
            self, executor, mock_ohlc_connector, mock_strategy, sample_candles,
    ):
        mock_strategy.warmup_candles = 10
        mock_ohlc_connector.fetch.return_value = sample_candles

        with patch('time.time', return_value=1700000120.0):
            executor._fetch_ohlc_history()

        args = mock_ohlc_connector.fetch.call_args[0]
        assert args[0] == 'XXBTZGBP'
        assert args[1] == 1

    def test_fetch_ohlc_history_calls_connector_with_since_based_on_warmup_candles(
            self, executor, mock_ohlc_connector, mock_strategy, sample_candles,
    ):
        # bot.interval=1, warmup_candles=10; since = now - 1 * 60 * (min(10, 720) + 1)
        mock_strategy.warmup_candles = 10
        mock_ohlc_connector.fetch.return_value = sample_candles
        frozen_time = 1700000120.0

        with patch('time.time', return_value=frozen_time):
            executor._fetch_ohlc_history()

        expected_since = int(frozen_time) - 1 * 60 * (10 + 1)
        args = mock_ohlc_connector.fetch.call_args[0]
        assert args[2] == expected_since

    def test_fetch_ohlc_history_caps_warmup_candles_at_720(
            self, executor, mock_ohlc_connector, mock_strategy, sample_candles,
    ):
        mock_strategy.warmup_candles = 1000
        mock_ohlc_connector.fetch.return_value = sample_candles
        frozen_time = 1700000120.0

        with patch('time.time', return_value=frozen_time):
            executor._fetch_ohlc_history()

        expected_since = int(frozen_time) - 1 * 60 * (720 + 1)
        args = mock_ohlc_connector.fetch.call_args[0]
        assert args[2] == expected_since

    def test_fetch_ohlc_history_returns_list_of_series(
            self, executor, mock_ohlc_connector, mock_strategy, sample_candles,
    ):
        mock_strategy.warmup_candles = 10
        mock_ohlc_connector.fetch.return_value = sample_candles

        with patch('time.time', return_value=1700000120.0):
            result = executor._fetch_ohlc_history()

        assert isinstance(result, list)
        assert all(isinstance(s, pd.Series) for s in result)

    def test_fetch_ohlc_history_returns_one_series_per_completed_candle(
            self, executor, mock_ohlc_connector, mock_strategy, sample_candles,
    ):
        mock_strategy.warmup_candles = 10
        mock_ohlc_connector.fetch.return_value = sample_candles

        with patch('time.time', return_value=1700000120.0):
            result = executor._fetch_ohlc_history()

        assert len(result) == len(sample_candles) - 1

    def test_fetch_ohlc_history_maps_ohlc_fields_correctly(
            self, executor, mock_ohlc_connector, mock_strategy, sample_candles,
    ):
        mock_strategy.warmup_candles = 10
        mock_ohlc_connector.fetch.return_value = sample_candles

        with patch('time.time', return_value=1700000120.0):
            result = executor._fetch_ohlc_history()

        for series, candle in zip(result, sample_candles[:-1]):
            assert series['open'] == candle.open
            assert series['high'] == candle.high
            assert series['low'] == candle.low
            assert series['close'] == candle.close

    def test_fetch_ohlc_history_series_contain_only_ohlc_keys(
            self, executor, mock_ohlc_connector, mock_strategy, sample_candles,
    ):
        mock_strategy.warmup_candles = 10
        mock_ohlc_connector.fetch.return_value = sample_candles

        with patch('time.time', return_value=1700000120.0):
            result = executor._fetch_ohlc_history()

        for series in result:
            assert list(series.index) == ['open', 'high', 'low', 'close']

    def test_fetch_ohlc_history_excludes_forming_candle(
            self, executor, mock_ohlc_connector, mock_strategy, sample_candles,
    ):
        # sample_candles[-1] is the forming candle; it must never appear in the result.
        mock_strategy.warmup_candles = 10
        mock_ohlc_connector.fetch.return_value = sample_candles
        forming_candle = sample_candles[-1]

        with patch('time.time', return_value=1700000120.0):
            result = executor._fetch_ohlc_history()

        result_closes = [s['close'] for s in result]
        assert forming_candle.close not in result_closes

    # --- _fetch_balances ---

    def test_fetch_balances_calls_balance_connector(self, executor, mock_balance_connector):
        mock_balance_connector.fetch.return_value = {'XXBT': '1.5', 'ZGBP': '10000.00'}

        executor._fetch_balances()

        mock_balance_connector.fetch.assert_called_once()

    def test_fetch_balances_returns_pair_balances_instance(self, executor, mock_balance_connector):
        mock_balance_connector.fetch.return_value = {'XXBT': '1.5', 'ZGBP': '10000.00'}

        result = executor._fetch_balances()

        assert isinstance(result, PairBalances)

    def test_fetch_balances_sets_correct_symbols(self, executor, mock_balance_connector):
        mock_balance_connector.fetch.return_value = {'XXBT': '1.5', 'ZGBP': '10000.00'}

        result = executor._fetch_balances()

        assert result.symbol_base == 'XXBT'
        assert result.symbol_quote == 'ZGBP'

    def test_fetch_balances_maps_balances_correctly(self, executor, mock_balance_connector):
        mock_balance_connector.fetch.return_value = {'XXBT': '1.5', 'ZGBP': '10000.00'}

        result = executor._fetch_balances()

        assert result.balance_base == Decimal('1.5')
        assert result.balance_quote == Decimal('10000.00')

    def test_fetch_balances_defaults_base_balance_to_zero_when_missing(self, executor, mock_balance_connector):
        mock_balance_connector.fetch.return_value = {'ZGBP': '10000.00'}

        result = executor._fetch_balances()

        assert result.balance_base == Decimal('0')

    def test_fetch_balances_defaults_quote_balance_to_zero_when_missing(self, executor, mock_balance_connector):
        mock_balance_connector.fetch.return_value = {'XXBT': '1.5'}

        result = executor._fetch_balances()

        assert result.balance_quote == Decimal('0')

    def test_fetch_balances_defaults_both_to_zero_when_response_is_empty(self, executor, mock_balance_connector):
        mock_balance_connector.fetch.return_value = {}

        result = executor._fetch_balances()

        assert result.balance_base == Decimal('0')
        assert result.balance_quote == Decimal('0')

    def test_fetch_balances_handles_numeric_balance_values(self, executor, mock_balance_connector):
        mock_balance_connector.fetch.return_value = {'XXBT': 1.5, 'ZGBP': 10000.0}

        result = executor._fetch_balances()

        assert result.balance_base == Decimal('1.5')
        assert result.balance_quote == Decimal('10000.0')

    # --- recover_state ---

    def test_recover_state_calls_repository_with_correct_bot_id(
            self, executor, mock_bot_tick_repo, bot,
    ):
        mock_bot_tick_repo.get_latest_action_by_bot_id.return_value = None

        executor.recover_state()

        mock_bot_tick_repo.get_latest_action_by_bot_id.assert_called_once_with(bot.id)

    def test_recover_state_sets_last_action_when_tick_found(
            self, executor, mock_bot_tick_repo, mock_strategy,
    ):
        mock_bot_tick_repo.get_latest_action_by_bot_id.return_value = Signal.BUY

        executor.recover_state()

        assert mock_strategy.last_action == Signal.BUY

    def test_recover_state_does_not_modify_last_action_when_no_tick_found(
            self, executor, mock_bot_tick_repo, mock_strategy,
    ):
        mock_bot_tick_repo.get_latest_action_by_bot_id.return_value = None
        mock_strategy.last_action = Signal.SELL

        executor.recover_state()

        assert mock_strategy.last_action == Signal.SELL

    # --- shutdown ---

    def test_shutdown_calls_complete_with_run_id(self, executor, mock_bot_run_repo):
        executor.shutdown()
        call_args = mock_bot_run_repo.complete.call_args[0]
        assert call_args[0] == executor.run.id

    def test_shutdown_calls_complete_with_utc_datetime(self, executor, mock_bot_run_repo):
        executor.shutdown()
        call_args = mock_bot_run_repo.complete.call_args[0]
        completed_at = call_args[1]
        assert completed_at.tzinfo is not None
        assert completed_at.tzinfo.utcoffset(completed_at).total_seconds() == 0

    def test_shutdown_logs_shutting_down_before_complete(self, executor, mock_bot_run_repo):
        # Given
        log_calls = []
        executor.logger = Mock()
        executor.logger.info.side_effect = lambda msg: log_calls.append(('info', msg))
        mock_bot_run_repo.complete.side_effect = lambda *_: log_calls.append(('complete', None))

        # When
        executor.shutdown()

        # Then — 'Shutting down...' must appear before the complete() call
        info_indices = [i for i, (kind, _) in enumerate(log_calls) if kind == 'info']
        complete_index = next(i for i, (kind, _) in enumerate(log_calls) if kind == 'complete')
        assert info_indices[0] < complete_index

    def test_shutdown_logs_shutdown_complete(self, executor):
        executor.logger = Mock()
        executor.shutdown()
        messages = [call.args[0] for call in executor.logger.info.call_args_list]
        assert 'Shutdown complete' in messages

    def test_shutdown_logs_error_when_complete_raises(self, executor, mock_bot_run_repo):
        mock_bot_run_repo.complete.side_effect = Exception('Supabase unreachable')
        executor.logger = Mock()
        executor.shutdown()
        executor.logger.error.assert_called_once()

    def test_shutdown_logs_shutdown_complete_even_when_complete_raises(
            self, executor, mock_bot_run_repo,
    ):
        # Shutdown should be best-effort — log the error but still log completion.
        mock_bot_run_repo.complete.side_effect = Exception('Supabase unreachable')
        executor.logger = Mock()
        executor.shutdown()
        messages = [call.args[0] for call in executor.logger.info.call_args_list]
        assert 'Shutdown complete' in messages

    # --- _reconcile_placed_orders ---

    @pytest.fixture
    def sample_placed_orders(self) -> list[BotOrder]:
        return [
            BotOrder(
                bot_id='btc_1m_001',
                run_id=uuid4(),
                exchange_order_id='TXID-AAA',
                side=Side.BUY,
            ),
            BotOrder(
                bot_id='btc_1m_001',
                run_id=uuid4(),
                exchange_order_id='TXID-BBB',
                side=Side.SELL,
            ),
        ]

    def _make_exchange_order(
            self, txid: str, status: QueryOrderStatus,
            price: str = '50000.00', volume: str = '0.001', fee: str = '0.50',
    ) -> QueryOrderResult:
        return QueryOrderResult(
            txid=txid,
            price=Decimal(price),
            volume=Decimal(volume),
            fee=Decimal(fee),
            status=status,
        )

    def test_reconcile_returns_early_when_no_placed_orders(
            self, executor, mock_bot_order_repo,
    ):
        mock_bot_order_repo.get_placed_by_bot_id.return_value = []

        executor._reconcile_placed_orders()

        mock_bot_order_repo.mark_filled.assert_not_called()
        mock_bot_order_repo.mark_failed.assert_not_called()

    def test_reconcile_does_not_call_exchange_when_no_placed_orders(
            self, executor, mock_bot_order_repo, mock_query_orders_connector,
    ):
        mock_bot_order_repo.get_placed_by_bot_id.return_value = []

        executor._reconcile_placed_orders()

        mock_query_orders_connector.fetch.assert_not_called()

    def test_reconcile_fetches_exchange_orders_by_exchange_ids(
            self, executor, mock_bot_order_repo, mock_query_orders_connector,
            sample_placed_orders,
    ):
        mock_bot_order_repo.get_placed_by_bot_id.return_value = sample_placed_orders
        mock_query_orders_connector.fetch.return_value = []

        executor._reconcile_placed_orders()

        txids = mock_query_orders_connector.fetch.call_args[0][0]
        assert set(txids) == {'TXID-AAA', 'TXID-BBB'}

    def test_reconcile_marks_closed_order_as_filled(
            self, executor, mock_bot_order_repo, mock_query_orders_connector,
            sample_placed_orders,
    ):
        order = sample_placed_orders[0]
        mock_bot_order_repo.get_placed_by_bot_id.return_value = [order]
        mock_query_orders_connector.fetch.return_value = [
            self._make_exchange_order('TXID-AAA', QueryOrderStatus.CLOSED),
        ]

        executor._reconcile_placed_orders()

        mock_bot_order_repo.mark_filled.assert_called_once_with(
            order.id, Decimal('50000.00'), Decimal('0.001'), Decimal('0.50'),
        )

    def test_reconcile_marks_canceled_order_as_failed(
            self, executor, mock_bot_order_repo, mock_query_orders_connector,
            sample_placed_orders,
    ):
        order = sample_placed_orders[0]
        mock_bot_order_repo.get_placed_by_bot_id.return_value = [order]
        mock_query_orders_connector.fetch.return_value = [
            self._make_exchange_order('TXID-AAA', QueryOrderStatus.CANCELED),
        ]

        executor._reconcile_placed_orders()

        mock_bot_order_repo.mark_failed.assert_called_once_with(
            order.id, Decimal('50000.00'), Decimal('0.001'), Decimal('0.50'),
        )

    def test_reconcile_marks_expired_order_as_failed(
            self, executor, mock_bot_order_repo, mock_query_orders_connector,
            sample_placed_orders,
    ):
        order = sample_placed_orders[0]
        mock_bot_order_repo.get_placed_by_bot_id.return_value = [order]
        mock_query_orders_connector.fetch.return_value = [
            self._make_exchange_order('TXID-AAA', QueryOrderStatus.EXPIRED),
        ]

        executor._reconcile_placed_orders()

        mock_bot_order_repo.mark_failed.assert_called_once_with(
            order.id, Decimal('50000.00'), Decimal('0.001'), Decimal('0.50'),
        )

    def test_reconcile_does_not_mark_open_order(
            self, executor, mock_bot_order_repo, mock_query_orders_connector,
            sample_placed_orders,
    ):
        mock_bot_order_repo.get_placed_by_bot_id.return_value = [sample_placed_orders[0]]
        mock_query_orders_connector.fetch.return_value = [
            self._make_exchange_order('TXID-AAA', QueryOrderStatus.OPEN),
        ]

        executor._reconcile_placed_orders()

        mock_bot_order_repo.mark_filled.assert_not_called()
        mock_bot_order_repo.mark_failed.assert_not_called()

    def test_reconcile_does_not_mark_pending_order(
            self, executor, mock_bot_order_repo, mock_query_orders_connector,
            sample_placed_orders,
    ):
        mock_bot_order_repo.get_placed_by_bot_id.return_value = [sample_placed_orders[0]]
        mock_query_orders_connector.fetch.return_value = [
            self._make_exchange_order('TXID-AAA', QueryOrderStatus.PENDING),
        ]

        executor._reconcile_placed_orders()

        mock_bot_order_repo.mark_filled.assert_not_called()
        mock_bot_order_repo.mark_failed.assert_not_called()

    def test_reconcile_handles_multiple_orders_with_different_statuses(
            self, executor, mock_bot_order_repo, mock_query_orders_connector,
            sample_placed_orders,
    ):
        mock_bot_order_repo.get_placed_by_bot_id.return_value = sample_placed_orders
        mock_query_orders_connector.fetch.return_value = [
            self._make_exchange_order('TXID-AAA', QueryOrderStatus.CLOSED,
                                      price='50000.00', volume='0.001', fee='0.50'),
            self._make_exchange_order('TXID-BBB', QueryOrderStatus.CANCELED,
                                      price='0', volume='0', fee='0'),
        ]

        executor._reconcile_placed_orders()

        mock_bot_order_repo.mark_filled.assert_called_once_with(
            sample_placed_orders[0].id,
            Decimal('50000.00'), Decimal('0.001'), Decimal('0.50'),
        )
        mock_bot_order_repo.mark_failed.assert_called_once_with(
            sample_placed_orders[1].id,
            Decimal('0'), Decimal('0'), Decimal('0'),
        )

    def test_reconcile_continues_after_single_order_error(
            self, executor, mock_bot_order_repo, mock_query_orders_connector,
            sample_placed_orders,
    ):
        # Given — first mark_filled raises, second should still proceed
        mock_bot_order_repo.get_placed_by_bot_id.return_value = sample_placed_orders
        mock_query_orders_connector.fetch.return_value = [
            self._make_exchange_order('TXID-AAA', QueryOrderStatus.CLOSED),
            self._make_exchange_order('TXID-BBB', QueryOrderStatus.CLOSED),
        ]
        mock_bot_order_repo.mark_filled.side_effect = [
            ValueError('Already resolved'),
            Mock(),
        ]

        # When
        executor._reconcile_placed_orders()

        # Then — mark_filled was attempted for both orders
        assert mock_bot_order_repo.mark_filled.call_count == 2

    def test_reconcile_logs_error_when_single_order_fails(
            self, executor, mock_bot_order_repo, mock_query_orders_connector,
            sample_placed_orders,
    ):
        mock_bot_order_repo.get_placed_by_bot_id.return_value = [sample_placed_orders[0]]
        mock_query_orders_connector.fetch.return_value = [
            self._make_exchange_order('TXID-AAA', QueryOrderStatus.CLOSED),
        ]
        mock_bot_order_repo.mark_filled.side_effect = ValueError('Already resolved')
        executor.logger = Mock()

        executor._reconcile_placed_orders()

        executor.logger.error.assert_called_once()
