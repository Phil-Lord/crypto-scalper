import logging
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch
from uuid import uuid4

import pandas as pd
import pytest

from data_system.models.bot_model import Bot
from data_system.models.bot_order_model import BotOrder, OrderStatus, Side
from data_system.models.bot_run_model import BotRun
from data_system.models.bot_tick_model import BotTick, Signal
from data_system.repositories.bot_order.bot_order_repository import BotOrderRepository
from data_system.repositories.bot_run.bot_run_repository import BotRunRepository
from data_system.repositories.bot_tick.bot_tick_repository import BotTickRepository
from exchange_connector.connectors.add_order_connector import AddOrderConnector
from exchange_connector.connectors.balance_connector import BalanceConnector
from exchange_connector.models.add_order_result import AddOrderResult
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
        executor.logger = Mock()

        executor.warm_up()

        assert mock_strategy.generate_signal.call_count == 3

    def test_warm_up_passes_each_ohlc_series_to_generate_signal(self, executor, mock_strategy):
        candles = [
            pd.Series({'open': 1.0, 'high': 2.0, 'low': 0.5, 'close': 1.5}),
            pd.Series({'open': 1.5, 'high': 2.5, 'low': 1.0, 'close': 2.0}),
        ]
        mock_strategy.warmup_candles = 2
        executor._fetch_ohlc_history = Mock(return_value=candles)
        executor.logger = Mock()

        executor.warm_up()

        calls = mock_strategy.generate_signal.call_args_list
        pd.testing.assert_series_equal(calls[0].args[0], candles[0])
        pd.testing.assert_series_equal(calls[1].args[0], candles[1])

    def test_warm_up_with_empty_history_does_not_call_generate_signal(self, executor, mock_strategy):
        mock_strategy.warmup_candles = 3
        executor._fetch_ohlc_history = Mock(return_value=[])
        executor.logger = Mock()

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

    def test_fetch_ohlc_raises_when_fewer_than_two_candles(self, executor, mock_ohlc_connector):
        mock_ohlc_connector.fetch.return_value = [OhlcCandle(
            timestamp=1700000000, open=50000.0, high=50100.0,
            low=49900.0, close=50050.0, vwap=50000.0, volume=100.0, count=50,
        )]

        with patch('time.time', return_value=1700000120.0):
            with pytest.raises(ValueError, match='Expected at least 2 OHLC candles'):
                executor._fetch_ohlc()

    def test_fetch_ohlc_raises_when_empty_response(self, executor, mock_ohlc_connector):
        mock_ohlc_connector.fetch.return_value = []

        with patch('time.time', return_value=1700000120.0):
            with pytest.raises(ValueError, match='Expected at least 2 OHLC candles'):
                executor._fetch_ohlc()

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

    @pytest.fixture
    def sample_buy_tick(self) -> BotTick:
        return BotTick(
            bot_id='btc_1m_001',
            run_id=uuid4(),
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            price=Decimal('50000.00'),
            signal=Signal.BUY,
            balance_base=Decimal('0'),
            balance_quote=Decimal('10000.00'),
        )

    @pytest.fixture
    def sample_sell_tick(self) -> BotTick:
        return BotTick(
            bot_id='btc_1m_001',
            run_id=uuid4(),
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            price=Decimal('50000.00'),
            signal=Signal.SELL,
            balance_base=Decimal('1.0'),
            balance_quote=Decimal('0'),
        )

    def test_recover_state_calls_repository_with_correct_bot_id(
            self, executor, mock_bot_tick_repo, bot,
    ):
        mock_bot_tick_repo.get_latest_action_by_bot_id.return_value = None

        executor.recover_state()

        mock_bot_tick_repo.get_latest_action_by_bot_id.assert_called_once_with(bot.id)

    def test_recover_state_sets_last_action_from_buy_tick(
            self, executor, mock_bot_tick_repo, mock_bot_order_repo,
            mock_strategy, sample_buy_tick,
    ):
        mock_bot_tick_repo.get_latest_action_by_bot_id.return_value = sample_buy_tick
        mock_bot_order_repo.get_by_tick_id.return_value = None

        executor.recover_state()

        assert mock_strategy.last_action == Signal.BUY

    def test_recover_state_sets_last_action_from_sell_tick(
            self, executor, mock_bot_tick_repo, mock_bot_order_repo,
            mock_strategy, sample_sell_tick,
    ):
        mock_bot_tick_repo.get_latest_action_by_bot_id.return_value = sample_sell_tick
        mock_bot_order_repo.get_by_tick_id.return_value = None

        executor.recover_state()

        assert mock_strategy.last_action == Signal.SELL

    def test_recover_state_resets_last_action_to_sell_when_no_tick_found(
            self, executor, mock_bot_tick_repo, mock_strategy,
    ):
        mock_bot_tick_repo.get_latest_action_by_bot_id.return_value = None
        mock_strategy.last_action = Signal.BUY

        executor.recover_state()

        assert mock_strategy.last_action == Signal.SELL

    def test_recover_state_logs_recovered_signal(
            self, executor, mock_bot_tick_repo, sample_buy_tick,
    ):
        mock_bot_tick_repo.get_latest_action_by_bot_id.return_value = sample_buy_tick
        executor.logger = Mock()

        executor.recover_state()

        info_messages = [str(call.args[0]) for call in executor.logger.info.call_args_list]
        assert any('buy' in msg.lower() for msg in info_messages)

    def test_recover_state_reverses_signal_when_associated_order_failed(
            self, executor, mock_bot_tick_repo, mock_bot_order_repo,
            mock_strategy, sample_buy_tick,
    ):
        mock_bot_tick_repo.get_latest_action_by_bot_id.return_value = sample_buy_tick
        mock_bot_order_repo.get_by_tick_id.return_value = BotOrder(
            bot_id='btc_1m_001', run_id=uuid4(),
            exchange_order_id='TXID-001', side=Side.BUY, status=OrderStatus.FAILED,
        )

        executor.recover_state()

        assert mock_strategy.last_action == Signal.SELL

    def test_recover_state_uses_tick_signal_when_associated_order_filled(
            self, executor, mock_bot_tick_repo, mock_bot_order_repo,
            mock_strategy, sample_buy_tick,
    ):
        mock_bot_tick_repo.get_latest_action_by_bot_id.return_value = sample_buy_tick
        mock_bot_order_repo.get_by_tick_id.return_value = BotOrder(
            bot_id='btc_1m_001', run_id=uuid4(),
            exchange_order_id='TXID-001', side=Side.BUY, status=OrderStatus.FILLED,
        )

        executor.recover_state()

        assert mock_strategy.last_action == Signal.BUY

    def test_recover_state_uses_tick_signal_when_no_order_for_tick(
            self, executor, mock_bot_tick_repo, mock_bot_order_repo,
            mock_strategy, sample_sell_tick,
    ):
        mock_bot_tick_repo.get_latest_action_by_bot_id.return_value = sample_sell_tick
        mock_bot_order_repo.get_by_tick_id.return_value = None

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

    def test_reconcile_handles_unexpected_exchange_order_id(
            self, executor, mock_bot_order_repo, mock_query_orders_connector,
            sample_placed_orders,
    ):
        # Exchange returns an order with a txid not in our placed orders map — should be
        # caught by the per-order try/except and logged, not crash reconciliation.
        mock_bot_order_repo.get_placed_by_bot_id.return_value = [sample_placed_orders[0]]
        mock_query_orders_connector.fetch.return_value = [
            self._make_exchange_order('TXID-UNKNOWN', QueryOrderStatus.CLOSED),
        ]
        executor.logger = Mock()

        executor._reconcile_placed_orders()

        executor.logger.error.assert_called_once()
        mock_bot_order_repo.mark_filled.assert_not_called()

    def test_reconcile_warns_when_order_missing_from_exchange_response(
            self, executor, mock_bot_order_repo, mock_query_orders_connector,
            sample_placed_orders,
    ):
        # Given — two placed orders, but exchange only returns one
        mock_bot_order_repo.get_placed_by_bot_id.return_value = sample_placed_orders
        mock_query_orders_connector.fetch.return_value = [
            self._make_exchange_order('TXID-AAA', QueryOrderStatus.CLOSED),
        ]
        executor.logger = Mock()

        # When
        executor._reconcile_placed_orders()

        # Then — warning logged for the missing order
        warning_messages = [str(call.args[0]) for call in executor.logger.warning.call_args_list]
        assert any('TXID-BBB' in msg and 'not returned' in msg for msg in warning_messages)

    def test_reconcile_rolls_back_last_action_when_canceled_order_matches(
            self, executor, mock_bot_order_repo, mock_query_orders_connector,
            mock_strategy, sample_placed_orders,
    ):
        order = sample_placed_orders[0]  # Side.BUY
        mock_bot_order_repo.get_placed_by_bot_id.return_value = [order]
        mock_query_orders_connector.fetch.return_value = [
            self._make_exchange_order('TXID-AAA', QueryOrderStatus.CANCELED),
        ]
        mock_strategy.last_action = Signal.BUY

        executor._reconcile_placed_orders()

        assert mock_strategy.last_action == Signal.SELL

    def test_reconcile_does_not_roll_back_last_action_when_failed_order_side_differs(
            self, executor, mock_bot_order_repo, mock_query_orders_connector,
            mock_strategy, sample_placed_orders,
    ):
        order = sample_placed_orders[0]  # Side.BUY
        mock_bot_order_repo.get_placed_by_bot_id.return_value = [order]
        mock_query_orders_connector.fetch.return_value = [
            self._make_exchange_order('TXID-AAA', QueryOrderStatus.CANCELED),
        ]
        mock_strategy.last_action = Signal.SELL  # Does not match order side (BUY)

        executor._reconcile_placed_orders()

        assert mock_strategy.last_action == Signal.SELL

    # --- _fetch_ohlc with different intervals ---

    def test_fetch_ohlc_since_calculation_with_five_minute_interval(
            self, bot, mock_strategy, mock_position_sizer, mock_bot_run_repo,
            mock_bot_tick_repo, mock_bot_order_repo, mock_balance_connector,
            mock_ohlc_connector, mock_add_order_connector, mock_query_orders_connector,
            sample_candles,
    ):
        five_min_bot = Bot(
            id='btc_5m_001', pair='XXBTZGBP', strategy_name='PrecisionTrendStrategy',
            strategy_version='v1.0.0', interval=5, parameters={'short_ema': 43},
        )
        executor = TradeExecutor(
            bot=five_min_bot, strategy=mock_strategy, position_sizer=mock_position_sizer,
            bot_run_repo=mock_bot_run_repo, bot_tick_repo=mock_bot_tick_repo,
            bot_order_repo=mock_bot_order_repo, balance_connector=mock_balance_connector,
            ohlc_connector=mock_ohlc_connector, add_order_connector=mock_add_order_connector,
            query_orders_connector=mock_query_orders_connector,
        )
        mock_ohlc_connector.fetch.return_value = sample_candles
        frozen_time = 1700000120.0

        with patch('time.time', return_value=frozen_time):
            executor._fetch_ohlc()

        # 5-minute interval: since = now - 5 * 60 * 2 = now - 600
        expected_since = int(frozen_time) - 5 * 60 * 2
        args = mock_ohlc_connector.fetch.call_args[0]
        assert args[2] == expected_since

    # --- execute_interval ---

    @pytest.fixture
    def exec_executor(
            self, executor, mock_strategy, mock_position_sizer,
            mock_bot_tick_repo, mock_bot_order_repo
    ):
        ''' Executor pre-configured for execute_interval tests with a HOLD baseline. '''
        executor._reconcile_placed_orders = Mock()
        executor._fetch_ohlc = Mock(return_value=pd.Series({
            'open': 49990.0, 'high': 50100.0, 'low': 49900.0, 'close': 50000.0,
        }))
        executor._fetch_balances = Mock(return_value=PairBalances(
            symbol_base='XXBT', symbol_quote='ZGBP',
            balance_base=Decimal('1.5'), balance_quote=Decimal('10000.00'),
        ))
        executor.logger = Mock()
        mock_strategy.last_action = Signal.SELL
        mock_strategy.generate_signal.return_value = {'signal': Signal.HOLD}
        mock_position_sizer.calculate_volume.return_value = Decimal('10000.00')
        mock_bot_tick_repo.add.side_effect = lambda tick: replace(tick, id=1)
        mock_bot_order_repo.add.side_effect = lambda order: order
        return executor

    def _make_order(self, executor, side=Side.BUY, status=OrderStatus.FILLED) -> BotOrder:
        return BotOrder(
            bot_id='btc_1m_001',
            run_id=executor.run.id,
            exchange_order_id='TXID-001',
            side=side,
            status=status,
            price=Decimal('50000.00') if status == OrderStatus.FILLED else Decimal('0'),
            volume=Decimal('0.001') if status == OrderStatus.FILLED else Decimal('0'),
            fee=Decimal('0.50') if status == OrderStatus.FILLED else Decimal('0'),
        )

    def _setup_order_signal(
            self, exec_executor, mock_strategy, mock_add_order_connector,
            signal, confirmed_order
    ):
        ''' Helper to configure a BUY/SELL signal with order placement and confirmation mocks. '''
        mock_strategy.generate_signal.return_value = {'signal': signal}
        mock_add_order_connector.place.return_value = AddOrderResult(
            txid=['TXID-001'],
            order_description=f'{signal.value} 0.001 XXBTZGBP @ market',
        )
        exec_executor._confirm_order = Mock(return_value=confirmed_order)

    # Shutdown

    def test_execute_interval_skipped_when_shutting_down(
            self, exec_executor, mock_bot_tick_repo
    ):
        exec_executor._shutting_down = True

        exec_executor.execute_interval()

        exec_executor._reconcile_placed_orders.assert_not_called()
        exec_executor._fetch_ohlc.assert_not_called()
        mock_bot_tick_repo.add.assert_not_called()

    # Reconciliation

    def test_execute_interval_calls_reconcile_at_start(self, exec_executor):
        exec_executor.execute_interval()

        exec_executor._reconcile_placed_orders.assert_called_once()

    def test_reconcile_exception_does_not_abort_interval(
            self, exec_executor, mock_bot_tick_repo
    ):
        exec_executor._reconcile_placed_orders.side_effect = Exception('Supabase timeout')

        exec_executor.execute_interval()

        mock_bot_tick_repo.add.assert_called_once()

    # OHLC failure

    def test_execute_interval_ohlc_failure_skips_tick(
            self, exec_executor, mock_strategy, mock_bot_tick_repo,
    ):
        exec_executor._fetch_ohlc.side_effect = Exception('Kraken unavailable')

        exec_executor.execute_interval()

        mock_strategy.generate_signal.assert_not_called()
        mock_bot_tick_repo.add.assert_not_called()

    # HOLD signal — happy path

    def test_execute_interval_hold_persists_tick_only(
            self, exec_executor, mock_bot_tick_repo, mock_bot_order_repo,
            mock_add_order_connector,
    ):
        exec_executor.execute_interval()

        mock_add_order_connector.place.assert_not_called()
        mock_bot_order_repo.add.assert_not_called()
        mock_bot_tick_repo.add.assert_called_once()
        tick = mock_bot_tick_repo.add.call_args[0][0]
        assert tick.signal == Signal.HOLD
        assert tick.bot_id == 'btc_1m_001'
        assert tick.price == Decimal('50000.0')
        assert tick.balance_base == Decimal('1.5')
        assert tick.balance_quote == Decimal('10000.00')
        assert tick.error is None

    def test_execute_interval_hold_fetches_balances_once(self, exec_executor):
        exec_executor.execute_interval()
        exec_executor._fetch_balances.assert_called_once()

    def test_execute_interval_tick_has_correct_run_id(
            self, exec_executor, mock_bot_tick_repo,
    ):
        exec_executor.execute_interval()
        tick = mock_bot_tick_repo.add.call_args[0][0]
        assert tick.run_id == exec_executor.run.id

    def test_execute_interval_tick_has_utc_timestamp(
            self, exec_executor, mock_bot_tick_repo,
    ):
        exec_executor.execute_interval()
        tick = mock_bot_tick_repo.add.call_args[0][0]
        assert tick.timestamp.tzinfo is not None
        assert tick.timestamp.tzinfo.utcoffset(tick.timestamp).total_seconds() == 0

    # BUY signal — order FILLED

    def test_execute_interval_buy_persists_tick_and_order(
            self, exec_executor, mock_strategy, mock_add_order_connector,
            mock_bot_tick_repo, mock_bot_order_repo,
    ):
        filled = self._make_order(exec_executor, side=Side.BUY, status=OrderStatus.FILLED)
        self._setup_order_signal(
            exec_executor, mock_strategy, mock_add_order_connector, Signal.BUY, filled,
        )

        exec_executor.execute_interval()

        mock_bot_tick_repo.add.assert_called_once()
        tick = mock_bot_tick_repo.add.call_args[0][0]
        assert tick.signal == Signal.BUY
        assert tick.price == Decimal('50000.0')
        assert tick.error is None

        mock_bot_order_repo.add.assert_called_once()
        order = mock_bot_order_repo.add.call_args[0][0]
        assert order.exchange_order_id == 'TXID-001'
        assert order.side == Side.BUY

    def test_execute_interval_sell_persists_tick_and_order(
            self, exec_executor, mock_strategy, mock_add_order_connector,
            mock_bot_tick_repo, mock_bot_order_repo,
    ):
        mock_strategy.last_action = Signal.BUY
        filled = self._make_order(exec_executor, side=Side.SELL, status=OrderStatus.FILLED)
        self._setup_order_signal(
            exec_executor, mock_strategy, mock_add_order_connector, Signal.SELL, filled,
        )

        exec_executor.execute_interval()

        tick = mock_bot_tick_repo.add.call_args[0][0]
        assert tick.signal == Signal.SELL
        order = mock_bot_order_repo.add.call_args[0][0]
        assert order.side == Side.SELL

    def test_execute_interval_buy_fetches_balances_after_order(
            self, exec_executor, mock_strategy, mock_add_order_connector,
    ):
        filled = self._make_order(exec_executor)
        self._setup_order_signal(
            exec_executor, mock_strategy, mock_add_order_connector, Signal.BUY, filled,
        )

        exec_executor.execute_interval()

        # Pre-order balances + post-order balances
        assert exec_executor._fetch_balances.call_count == 2

    def test_execute_interval_buy_links_order_to_tick(
            self, exec_executor, mock_strategy, mock_add_order_connector,
            mock_bot_order_repo,
    ):
        filled = self._make_order(exec_executor)
        self._setup_order_signal(
            exec_executor, mock_strategy, mock_add_order_connector, Signal.BUY, filled,
        )

        exec_executor.execute_interval()

        mock_bot_order_repo.update.assert_called_once()
        linked_order = mock_bot_order_repo.update.call_args[0][0]
        assert linked_order.tick_id == 1

    def test_execute_interval_bot_order_side_is_side_enum_not_signal_enum(
            self, exec_executor, mock_strategy, mock_add_order_connector,
            mock_bot_order_repo,
    ):
        filled = self._make_order(exec_executor)
        self._setup_order_signal(
            exec_executor, mock_strategy, mock_add_order_connector, Signal.BUY, filled,
        )

        exec_executor.execute_interval()

        order = mock_bot_order_repo.add.call_args[0][0]
        assert isinstance(order.side, Side)

    # BUY signal — order FAILED

    def test_execute_interval_failed_order_tick_has_hold_signal(
            self, exec_executor, mock_strategy, mock_add_order_connector,
            mock_bot_tick_repo,
    ):
        failed = self._make_order(exec_executor, status=OrderStatus.FAILED)
        self._setup_order_signal(
            exec_executor, mock_strategy, mock_add_order_connector, Signal.BUY, failed,
        )

        exec_executor.execute_interval()

        tick = mock_bot_tick_repo.add.call_args[0][0]
        assert tick.signal == Signal.HOLD

    def test_execute_interval_failed_order_tick_has_error_set(
            self, exec_executor, mock_strategy, mock_add_order_connector,
            mock_bot_tick_repo,
    ):
        failed = self._make_order(exec_executor, status=OrderStatus.FAILED)
        self._setup_order_signal(
            exec_executor, mock_strategy, mock_add_order_connector, Signal.BUY, failed,
        )

        exec_executor.execute_interval()

        tick = mock_bot_tick_repo.add.call_args[0][0]
        assert tick.error is not None
        assert 'failed' in tick.error.lower()

    def test_execute_interval_failed_order_rolls_back_last_action(
            self, exec_executor, mock_strategy, mock_add_order_connector,
    ):
        # Given — last action is SELL, strategy generates BUY, order fails
        mock_strategy.last_action = Signal.SELL
        failed = self._make_order(exec_executor, status=OrderStatus.FAILED)
        self._setup_order_signal(
            exec_executor, mock_strategy, mock_add_order_connector, Signal.BUY, failed,
        )

        exec_executor.execute_interval()

        assert mock_strategy.last_action == Signal.SELL

    def test_execute_interval_failed_order_still_linked_to_tick(
            self, exec_executor, mock_strategy, mock_add_order_connector,
            mock_bot_order_repo,
    ):
        failed = self._make_order(exec_executor, status=OrderStatus.FAILED)
        self._setup_order_signal(
            exec_executor, mock_strategy, mock_add_order_connector, Signal.BUY, failed,
        )

        exec_executor.execute_interval()

        mock_bot_order_repo.update.assert_called_once()
        linked_order = mock_bot_order_repo.update.call_args[0][0]
        assert linked_order.tick_id == 1

    # Dry run

    def test_execute_interval_dry_run_validates_without_placing(
            self, exec_executor, mock_strategy, mock_add_order_connector,
            mock_bot_order_repo, mock_bot_tick_repo,
    ):
        exec_executor.dry_run = True
        mock_strategy.generate_signal.return_value = {'signal': Signal.BUY}
        mock_add_order_connector.place.return_value = AddOrderResult(
            txid=None, order_description='buy 0.001 XXBTZGBP @ market',
        )

        exec_executor.execute_interval()

        mock_add_order_connector.place.assert_called_once_with(
            'XXBTZGBP', Signal.BUY, Decimal('10000.00'), validate=True,
        )
        mock_bot_order_repo.add.assert_not_called()
        mock_bot_tick_repo.add.assert_not_called()

    def test_execute_interval_dry_run_logs_without_persisting_tick(
            self, exec_executor, mock_strategy, mock_add_order_connector,
            mock_bot_tick_repo,
    ):
        exec_executor.dry_run = True
        mock_strategy.generate_signal.return_value = {'signal': Signal.BUY}
        mock_add_order_connector.place.return_value = AddOrderResult(
            txid=None, order_description='buy 0.001 XXBTZGBP @ market',
        )

        exec_executor.execute_interval()

        mock_bot_tick_repo.add.assert_not_called()
        log_messages = [str(call.args[1]) for call in exec_executor.logger.log.call_args_list]
        assert any('DRY RUN' in msg and '50000.0' in msg for msg in log_messages)

    def test_execute_interval_dry_run_hold_logs_at_debug_level(self, exec_executor, mock_strategy):
        exec_executor.dry_run = True
        mock_strategy.generate_signal.return_value = {'signal': Signal.HOLD}

        exec_executor.execute_interval()

        log_calls = exec_executor.logger.log.call_args_list
        dry_run_calls = [c for c in log_calls if 'DRY RUN' in str(c.args[1])]
        assert len(dry_run_calls) == 1
        assert dry_run_calls[0].args[0] == logging.DEBUG

    def test_execute_interval_dry_run_buy_logs_at_info_level(
            self, exec_executor, mock_strategy, mock_add_order_connector,
    ):
        exec_executor.dry_run = True
        mock_strategy.generate_signal.return_value = {'signal': Signal.BUY}
        mock_add_order_connector.place.return_value = AddOrderResult(
            txid=None, order_description='buy 0.001 XXBTZGBP @ market',
        )

        exec_executor.execute_interval()

        log_calls = exec_executor.logger.log.call_args_list
        dry_run_calls = [c for c in log_calls if 'DRY RUN' in str(c.args[1])]
        assert len(dry_run_calls) == 1
        assert dry_run_calls[0].args[0] == logging.INFO

    # Logging — signal and order submission

    def test_execute_interval_buy_logs_signal_and_price(
            self, exec_executor, mock_strategy, mock_add_order_connector,
    ):
        filled = self._make_order(exec_executor, side=Side.BUY, status=OrderStatus.FILLED)
        self._setup_order_signal(
            exec_executor, mock_strategy, mock_add_order_connector, Signal.BUY, filled,
        )

        exec_executor.execute_interval()

        info_messages = [str(call.args[0]) for call in exec_executor.logger.info.call_args_list]
        assert any('Signal generated: signal=buy' in msg and '50000.0' in msg for msg in info_messages)

    def test_execute_interval_buy_logs_order_submission_details(
            self, exec_executor, mock_strategy, mock_add_order_connector,
    ):
        filled = self._make_order(exec_executor, side=Side.BUY, status=OrderStatus.FILLED)
        self._setup_order_signal(
            exec_executor, mock_strategy, mock_add_order_connector, Signal.BUY, filled,
        )

        exec_executor.execute_interval()

        info_messages = [str(call.args[0]) for call in exec_executor.logger.info.call_args_list]
        assert any(
            'TXID-001' in msg and 'buy' in msg and '10000' in msg
            for msg in info_messages
        )

    # Logging — interval completion levels

    def test_execute_interval_hold_logs_completion_at_debug_level(self, exec_executor):
        exec_executor.execute_interval()

        debug_messages = [str(call.args[0]) for call in exec_executor.logger.debug.call_args_list]
        assert any('Interval complete' in msg and 'hold' in msg for msg in debug_messages)

    def test_execute_interval_buy_logs_completion_at_info_level_with_balances(
            self, exec_executor, mock_strategy, mock_add_order_connector,
    ):
        filled = self._make_order(exec_executor, side=Side.BUY, status=OrderStatus.FILLED)
        self._setup_order_signal(
            exec_executor, mock_strategy, mock_add_order_connector, Signal.BUY, filled,
        )

        exec_executor.execute_interval()

        info_messages = [str(call.args[0]) for call in exec_executor.logger.info.call_args_list]
        assert any(
            'Interval complete' in msg and 'balance_base' in msg
            for msg in info_messages
        )

    # Error flows — strategy exception

    def test_execute_interval_strategy_error_persists_tick_with_error(
            self, exec_executor, mock_strategy, mock_bot_tick_repo,
    ):
        mock_strategy.generate_signal.side_effect = Exception('Strategy failed oh no!')

        exec_executor.execute_interval()

        mock_bot_tick_repo.add.assert_called_once()
        tick = mock_bot_tick_repo.add.call_args[0][0]
        assert tick.signal == Signal.HOLD
        assert tick.error == 'Strategy failed oh no!'

    def test_execute_interval_last_action_rolled_back_on_pre_order_exception(
            self, exec_executor, mock_strategy, mock_add_order_connector,
    ):
        # Given — BUY signal but balance fetch (pre-order) raises before order creation
        mock_strategy.last_action = Signal.SELL

        def mock_generate_signal(ohlc):
            mock_strategy.last_action = Signal.BUY
            return {'signal': Signal.BUY}

        mock_strategy.generate_signal.side_effect = mock_generate_signal
        exec_executor._fetch_balances = Mock(side_effect=[
            Exception('Balance unavailable'),
            PairBalances(
                symbol_base='XXBT', symbol_quote='ZGBP',
                balance_base=Decimal('0'), balance_quote=Decimal('0'),
            ),
        ])

        exec_executor.execute_interval()

        assert mock_strategy.last_action == Signal.SELL
        mock_add_order_connector.place.assert_not_called()

    # Error flows — post-order exception

    def test_execute_interval_exception_after_order_persisted_tick_records_order_direction(
            self, exec_executor, mock_strategy, mock_add_order_connector,
            mock_bot_tick_repo,
    ):
        # Given — BUY signal, order placed, then _confirm_order raises
        mock_strategy.generate_signal.return_value = {'signal': Signal.BUY}
        mock_add_order_connector.place.return_value = AddOrderResult(
            txid=['TXID-001'], order_description='buy 0.001 XXBTZGBP @ market',
        )
        exec_executor._confirm_order = Mock(side_effect=Exception('Confirm failed oh no!'))

        exec_executor.execute_interval()

        tick = mock_bot_tick_repo.add.call_args[0][0]
        assert tick.signal == Signal.BUY
        assert tick.error == 'Confirm failed oh no!'

    def test_execute_interval_last_action_not_rolled_back_when_order_persisted(
            self, exec_executor, mock_strategy, mock_add_order_connector,
    ):
        # Given — strategy changes last_action to BUY, then error after order persisted
        mock_strategy.last_action = Signal.SELL

        def mock_generate_signal(ohlc):
            mock_strategy.last_action = Signal.BUY
            return {'signal': Signal.BUY}

        mock_strategy.generate_signal.side_effect = mock_generate_signal
        mock_add_order_connector.place.return_value = AddOrderResult(
            txid=['TXID-001'], order_description='buy 0.001 XXBTZGBP @ market',
        )
        exec_executor._confirm_order = Mock(side_effect=Exception('Confirm failed oh no!'))

        exec_executor.execute_interval()

        # last_action NOT rolled back because placed_order exists
        assert mock_strategy.last_action == Signal.BUY

    def test_execute_interval_balance_error_in_error_handler_returns_early(
            self, exec_executor, mock_strategy, mock_bot_tick_repo,
    ):
        # Given — strategy raises, then balance fetch in error handler also raises
        mock_strategy.generate_signal.side_effect = Exception('Strategy error')
        exec_executor._fetch_balances = Mock(side_effect=Exception('Balance error'))

        exec_executor.execute_interval()

        mock_bot_tick_repo.add.assert_not_called()

    # Tick and order persistence errors

    def test_execute_interval_tick_persistence_failure_logs_and_returns(
            self, exec_executor, mock_strategy, mock_add_order_connector,
            mock_bot_tick_repo, mock_bot_order_repo,
    ):
        # Given — BUY signal with order, but tick persistence fails
        filled = self._make_order(exec_executor)
        self._setup_order_signal(
            exec_executor, mock_strategy, mock_add_order_connector, Signal.BUY, filled,
        )
        mock_bot_tick_repo.add.side_effect = Exception('Supabase write failed')

        exec_executor.execute_interval()

        exec_executor.logger.error.assert_called()
        mock_bot_order_repo.update.assert_not_called()

    def test_execute_interval_order_link_failure_logs_but_interval_completes(
            self, exec_executor, mock_strategy, mock_add_order_connector,
            mock_bot_order_repo,
    ):
        filled = self._make_order(exec_executor)
        self._setup_order_signal(
            exec_executor, mock_strategy, mock_add_order_connector, Signal.BUY, filled,
        )
        mock_bot_order_repo.update.side_effect = Exception('Update failed')

        exec_executor.execute_interval()

        exec_executor.logger.error.assert_called()
        log_messages = [str(call.args[0]) for call in exec_executor.logger.info.call_args_list]
        assert any('complete' in msg.lower() for msg in log_messages)

    # Dry run — reconciliation

    def test_execute_interval_dry_run_still_reconciles(
            self, exec_executor,
    ):
        exec_executor.dry_run = True
        exec_executor.execute_interval()
        exec_executor._reconcile_placed_orders.assert_called_once()

    # --- _confirm_order ---

    def test_confirm_order_retries_three_times_when_still_open(
            self, executor, mock_query_orders_connector, mock_bot_order_repo,
    ):
        order = BotOrder(
            bot_id='btc_1m_001', run_id=executor.run.id,
            exchange_order_id='TXID-001', side=Side.BUY,
        )
        mock_query_orders_connector.fetch.return_value = [
            QueryOrderResult(
                txid='TXID-001', price=Decimal('0'), volume=Decimal('0'),
                fee=Decimal('0'), status=QueryOrderStatus.OPEN,
            ),
        ]
        executor.logger = Mock()

        with patch('time.sleep'):
            result = executor._confirm_order(order)

        assert mock_query_orders_connector.fetch.call_count == 3
        assert result.status == OrderStatus.PLACED

    def test_confirm_order_marks_filled_when_closed(
            self, executor, mock_query_orders_connector, mock_bot_order_repo,
    ):
        order = BotOrder(
            bot_id='btc_1m_001', run_id=executor.run.id,
            exchange_order_id='TXID-001', side=Side.BUY,
        )
        filled_order = replace(
            order, status=OrderStatus.FILLED, price=Decimal('50000.00'),
            volume=Decimal('0.001'), fee=Decimal('0.50'),
        )
        mock_query_orders_connector.fetch.return_value = [
            QueryOrderResult(
                txid='TXID-001', price=Decimal('50000.00'), volume=Decimal('0.001'),
                fee=Decimal('0.50'), status=QueryOrderStatus.CLOSED,
            ),
        ]
        mock_bot_order_repo.mark_filled.return_value = filled_order
        executor.logger = Mock()

        result = executor._confirm_order(order)

        mock_bot_order_repo.mark_filled.assert_called_once_with(
            order.id, Decimal('50000.00'), Decimal('0.001'), Decimal('0.50'),
        )
        assert result.status == OrderStatus.FILLED

    def test_confirm_order_marks_failed_when_cancelled(
            self, executor, mock_query_orders_connector, mock_bot_order_repo,
    ):
        order = BotOrder(
            bot_id='btc_1m_001', run_id=executor.run.id,
            exchange_order_id='TXID-001', side=Side.BUY,
        )
        failed_order = replace(order, status=OrderStatus.FAILED)
        mock_query_orders_connector.fetch.return_value = [
            QueryOrderResult(
                txid='TXID-001', price=Decimal('0'), volume=Decimal('0'),
                fee=Decimal('0'), status=QueryOrderStatus.CANCELED,
            ),
        ]
        mock_bot_order_repo.mark_failed.return_value = failed_order
        executor.logger = Mock()

        result = executor._confirm_order(order)

        mock_bot_order_repo.mark_failed.assert_called_once()
        assert result.status == OrderStatus.FAILED

    # --- execute_interval — fill confirmation through real _confirm_order ---
    #
    # These tests exercise the full BUY → submit → QueryOrders confirm path with
    # `_confirm_order` running for real. The other execute_interval tests mock
    # `_confirm_order` via `_setup_order_signal` to focus on tick/order persistence;
    # these complement them by covering the live confirmation flow end-to-end.

    def _setup_live_buy(self, exec_executor, mock_strategy, mock_add_order_connector):
        ''' Configures a live BUY signal with a real (unmocked) _confirm_order path. '''
        mock_strategy.last_action = Signal.SELL

        def generate(_ohlc):
            # Mirror the real Strategy: mutate last_action when emitting a directional signal.
            mock_strategy.last_action = Signal.BUY
            return {'signal': Signal.BUY}

        mock_strategy.generate_signal.side_effect = generate
        mock_add_order_connector.place.return_value = AddOrderResult(
            txid=['TXID-001'], order_description='buy 0.001 XXBTZGBP @ market',
        )

    def test_execute_interval_query_fill_retries_three_times(
            self, exec_executor, mock_strategy, mock_add_order_connector,
            mock_query_orders_connector,
    ):
        # Given — order placed but Kraken keeps reporting OPEN; confirm should retry 3×
        self._setup_live_buy(exec_executor, mock_strategy, mock_add_order_connector)
        mock_query_orders_connector.fetch.return_value = [
            QueryOrderResult(
                txid='TXID-001', price=Decimal('0'), volume=Decimal('0'),
                fee=Decimal('0'), status=QueryOrderStatus.OPEN,
            ),
        ]

        with patch('time.sleep') as mock_sleep:
            exec_executor.execute_interval()

        assert mock_query_orders_connector.fetch.call_count == 3
        # Two sleeps between three attempts, each one second.
        assert mock_sleep.call_count == 2
        for call in mock_sleep.call_args_list:
            assert call.args[0] == 1

    def test_execute_interval_query_fill_still_open_leaves_placed(
            self, exec_executor, mock_strategy, mock_add_order_connector,
            mock_query_orders_connector, mock_bot_order_repo,
    ):
        # Given — Kraken keeps reporting OPEN through all retries
        self._setup_live_buy(exec_executor, mock_strategy, mock_add_order_connector)
        mock_query_orders_connector.fetch.return_value = [
            QueryOrderResult(
                txid='TXID-001', price=Decimal('0'), volume=Decimal('0'),
                fee=Decimal('0'), status=QueryOrderStatus.OPEN,
            ),
        ]

        with patch('time.sleep'):
            exec_executor.execute_interval()

        # Order persisted as PLACED, never marked filled or failed; will reconcile next interval.
        mock_bot_order_repo.add.assert_called_once()
        added_order = mock_bot_order_repo.add.call_args[0][0]
        assert added_order.status == OrderStatus.PLACED
        mock_bot_order_repo.mark_filled.assert_not_called()
        mock_bot_order_repo.mark_failed.assert_not_called()
        # last_action stays advanced — order is in DB and may yet fill.
        assert mock_strategy.last_action == Signal.BUY

    def test_execute_interval_query_fill_cancelled_marks_failed(
            self, exec_executor, mock_strategy, mock_add_order_connector,
            mock_query_orders_connector, mock_bot_order_repo, mock_bot_tick_repo,
    ):
        # Given — Kraken reports CANCELED on first poll
        self._setup_live_buy(exec_executor, mock_strategy, mock_add_order_connector)
        mock_query_orders_connector.fetch.return_value = [
            QueryOrderResult(
                txid='TXID-001', price=Decimal('0'), volume=Decimal('0'),
                fee=Decimal('0'), status=QueryOrderStatus.CANCELED,
            ),
        ]
        # `mark_failed` returns the FAILED-status order so execute_interval can route to HOLD.
        mock_bot_order_repo.mark_failed.return_value = self._make_order(
            exec_executor, side=Side.BUY, status=OrderStatus.FAILED,
        )

        with patch('time.sleep'):
            exec_executor.execute_interval()

        mock_bot_order_repo.mark_failed.assert_called_once()
        # last_action rolled back because the order never executed.
        assert mock_strategy.last_action == Signal.SELL
        # Tick records HOLD (no real position change) with an error string.
        tick = mock_bot_tick_repo.add.call_args[0][0]
        assert tick.signal == Signal.HOLD
        assert tick.error is not None

    def test_execute_interval_query_fill_closed_marks_filled(
            self, exec_executor, mock_strategy, mock_add_order_connector,
            mock_query_orders_connector, mock_bot_order_repo,
    ):
        # Given — Kraken reports CLOSED with fill details on first poll
        self._setup_live_buy(exec_executor, mock_strategy, mock_add_order_connector)
        mock_query_orders_connector.fetch.return_value = [
            QueryOrderResult(
                txid='TXID-001', price=Decimal('50000.00'), volume=Decimal('0.001'),
                fee=Decimal('0.50'), status=QueryOrderStatus.CLOSED,
            ),
        ]
        mock_bot_order_repo.mark_filled.return_value = self._make_order(
            exec_executor, side=Side.BUY, status=OrderStatus.FILLED,
        )

        exec_executor.execute_interval()

        # Single QueryOrders call — closed on first attempt, no retries needed.
        assert mock_query_orders_connector.fetch.call_count == 1
        mock_bot_order_repo.mark_filled.assert_called_once_with(
            mock_bot_order_repo.add.call_args[0][0].id,
            Decimal('50000.00'), Decimal('0.001'), Decimal('0.50'),
        )

    # --- warm_up — must not touch persistence or place orders ---

    def test_warm_up_does_not_persist_ticks(
            self, executor, mock_strategy, mock_bot_tick_repo,
    ):
        candles = [
            pd.Series({'open': 1.0, 'high': 2.0, 'low': 0.5, 'close': 1.5}),
            pd.Series({'open': 1.5, 'high': 2.5, 'low': 1.0, 'close': 2.0}),
        ]
        mock_strategy.warmup_candles = 2
        executor._fetch_ohlc_history = Mock(return_value=candles)
        executor.logger = Mock()

        executor.warm_up()

        mock_bot_tick_repo.add.assert_not_called()

    def test_warm_up_does_not_place_orders(
            self, executor, mock_strategy, mock_add_order_connector, mock_bot_order_repo,
    ):
        candles = [
            pd.Series({'open': 1.0, 'high': 2.0, 'low': 0.5, 'close': 1.5}),
            pd.Series({'open': 1.5, 'high': 2.5, 'low': 1.0, 'close': 2.0}),
        ]
        mock_strategy.warmup_candles = 2
        executor._fetch_ohlc_history = Mock(return_value=candles)
        executor.logger = Mock()

        executor.warm_up()

        mock_add_order_connector.place.assert_not_called()
        mock_bot_order_repo.add.assert_not_called()

    # --- execute_interval — argument propagation to dependencies ---

    def test_execute_interval_position_sizer_receives_signal_and_pre_order_balances(
            self, exec_executor, mock_strategy, mock_position_sizer, mock_add_order_connector,
    ):
        # Given — pre-order balances differ from post-order (verifies the *pre* set is sized)
        pre_order = PairBalances(
            symbol_base='XXBT', symbol_quote='ZGBP',
            balance_base=Decimal('0'), balance_quote=Decimal('10000.00'),
        )
        post_order = PairBalances(
            symbol_base='XXBT', symbol_quote='ZGBP',
            balance_base=Decimal('0.2'), balance_quote=Decimal('0'),
        )
        exec_executor._fetch_balances = Mock(side_effect=[pre_order, post_order])

        filled = self._make_order(exec_executor, side=Side.BUY, status=OrderStatus.FILLED)
        self._setup_order_signal(
            exec_executor, mock_strategy, mock_add_order_connector, Signal.BUY, filled,
        )

        exec_executor.execute_interval()

        mock_position_sizer.calculate_volume.assert_called_once_with(Signal.BUY, pre_order)

    def test_execute_interval_add_order_called_with_pair_signal_and_volume(
            self, exec_executor, mock_strategy, mock_position_sizer, mock_add_order_connector,
    ):
        mock_position_sizer.calculate_volume.return_value = Decimal('0.005')
        filled = self._make_order(exec_executor, side=Side.BUY, status=OrderStatus.FILLED)
        self._setup_order_signal(
            exec_executor, mock_strategy, mock_add_order_connector, Signal.BUY, filled,
        )

        exec_executor.execute_interval()

        mock_add_order_connector.place.assert_called_once_with(
            'XXBTZGBP', Signal.BUY, Decimal('0.005'), validate=False,
        )

    def test_execute_interval_post_order_balances_persisted_in_tick(
            self, exec_executor, mock_strategy, mock_add_order_connector, mock_bot_tick_repo,
    ):
        # Given — pre-order is all-quote, post-order is all-base (a successful BUY swap)
        pre_order = PairBalances(
            symbol_base='XXBT', symbol_quote='ZGBP',
            balance_base=Decimal('0'), balance_quote=Decimal('10000.00'),
        )
        post_order = PairBalances(
            symbol_base='XXBT', symbol_quote='ZGBP',
            balance_base=Decimal('0.2'), balance_quote=Decimal('0'),
        )
        exec_executor._fetch_balances = Mock(side_effect=[pre_order, post_order])

        filled = self._make_order(exec_executor, side=Side.BUY, status=OrderStatus.FILLED)
        self._setup_order_signal(
            exec_executor, mock_strategy, mock_add_order_connector, Signal.BUY, filled,
        )

        exec_executor.execute_interval()

        tick = mock_bot_tick_repo.add.call_args[0][0]
        assert tick.balance_base == Decimal('0.2')
        assert tick.balance_quote == Decimal('0')

    def test_execute_interval_raises_when_live_order_returns_no_txid(
            self, exec_executor, mock_strategy, mock_add_order_connector, mock_bot_tick_repo,
    ):
        # Given — Kraken returns no txid in live mode (should never happen outside validate=True)
        mock_strategy.generate_signal.return_value = {'signal': Signal.BUY}
        mock_add_order_connector.place.return_value = AddOrderResult(
            txid=None, order_description='buy 0.001 XXBTZGBP @ market',
        )

        exec_executor.execute_interval()

        # The ValueError is caught by the signal/order block; tick is persisted with the error.
        tick = mock_bot_tick_repo.add.call_args[0][0]
        assert tick.signal == Signal.HOLD
        assert tick.error is not None
        assert 'txid' in tick.error.lower()

    # --- request_shutdown vs shutdown — separation of responsibilities ---

    def test_request_shutdown_does_not_complete_run(
            self, executor, mock_bot_run_repo,
    ):
        executor.request_shutdown()
        mock_bot_run_repo.complete.assert_not_called()
