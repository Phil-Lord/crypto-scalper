import logging
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from data_system.models.bot_model import Bot
from data_system.models.bot_run_model import BotRun
from data_system.repositories.bot_order.bot_order_repository import BotOrderRepository
from data_system.repositories.bot_run.bot_run_repository import BotRunRepository
from data_system.repositories.bot_tick.bot_tick_repository import BotTickRepository
from exchange_connector.connectors.add_order_connector import AddOrderConnector
from exchange_connector.connectors.balance_connector import BalanceConnector
from exchange_connector.connectors.ohlc_connector import OhlcConnector
from exchange_connector.models.ohlc_candle import OhlcCandle
from exchange_connector.connectors.query_orders_connector import QueryOrdersConnector
from strategy_manager.strategies.base_strategy import Strategy
from trade_executor.position_sizer import PositionSizer
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
