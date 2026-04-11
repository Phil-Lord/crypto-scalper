from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from data_system.models.bot_model import Bot
from scripts.start_scalping import interval_to_cron, start_scalping


def _make_bot(bot_id: str = 'btc_1m_001', interval: int = 1) -> Bot:
    return Bot(
        id=bot_id,
        pair='XXBTZGBP',
        strategy_name='SmaStrategy',
        strategy_version='v1.0.0',
        interval=interval,
        parameters={'short_window': 10, 'long_window': 20},
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


MODULE = 'scripts.start_scalping'


@pytest.mark.scripts
@pytest.mark.start_scalping
class TestStartScalping:

    @pytest.fixture
    def mock_bot_repository(self):
        with patch(f'{MODULE}.SupabaseBotRepository') as cls:
            repo = Mock()
            cls.return_value = repo
            yield repo

    @pytest.fixture
    def mock_supabase_client(self):
        with patch(f'{MODULE}.SupabaseClient') as cls:
            cls.return_value = Mock()
            yield cls

    @pytest.fixture
    def mock_create_strategy(self):
        with patch(f'{MODULE}.create_strategy') as fn:
            fn.return_value = Mock()
            yield fn

    @pytest.fixture
    def mock_position_sizer(self):
        with patch(f'{MODULE}.AllInPositionSizer') as cls:
            cls.return_value = Mock()
            yield cls

    @pytest.fixture
    def mock_trade_executor_cls(self):
        with patch(f'{MODULE}.TradeExecutor') as cls:
            executor = Mock()
            cls.return_value = executor
            yield cls

    @pytest.fixture
    def mock_scheduler(self):
        with patch(f'{MODULE}.BlockingScheduler') as cls:
            scheduler = Mock()
            cls.return_value = scheduler
            yield scheduler

    @pytest.fixture
    def mock_connectors(self):
        with patch(f'{MODULE}.BalanceConnector') as balance, \
                patch(f'{MODULE}.OhlcConnector') as ohlc, \
                patch(f'{MODULE}.AddOrderConnector') as add_order, \
                patch(f'{MODULE}.QueryOrdersConnector') as query_orders:
            yield {
                'balance': balance,
                'ohlc': ohlc,
                'add_order': add_order,
                'query_orders': query_orders,
            }

    @pytest.fixture
    def mock_signal(self):
        with patch(f'{MODULE}.signal') as sig:
            yield sig

    @pytest.fixture
    def all_mocks(
        self, mock_bot_repository, mock_supabase_client, mock_create_strategy,
        mock_position_sizer, mock_trade_executor_cls, mock_scheduler,
        mock_connectors, mock_signal,
    ):
        '''Convenience fixture that activates all patches.'''
        return {
            'bot_repo': mock_bot_repository,
            'supabase_client': mock_supabase_client,
            'create_strategy': mock_create_strategy,
            'position_sizer': mock_position_sizer,
            'trade_executor_cls': mock_trade_executor_cls,
            'scheduler': mock_scheduler,
            'connectors': mock_connectors,
            'signal': mock_signal,
        }

    # --- Single bot ---

    def test_creates_executor_for_valid_bot(self, all_mocks):
        bot = _make_bot()
        all_mocks['bot_repo'].get.return_value = bot

        start_scalping.main(['--bot-id', 'btc_1m_001'], standalone_mode=False)

        all_mocks['trade_executor_cls'].assert_called_once()
        call_args = all_mocks['trade_executor_cls'].call_args
        # TradeExecutor is called with positional args in the script
        assert call_args.args[0] is bot
        assert call_args.kwargs.get('dry_run', False) is False

    def test_calls_warm_up_and_recover_state(self, all_mocks):
        all_mocks['bot_repo'].get.return_value = _make_bot()
        executor = all_mocks['trade_executor_cls'].return_value

        start_scalping.main(['--bot-id', 'btc_1m_001'], standalone_mode=False)

        executor.warm_up.assert_called_once()
        executor.recover_state.assert_called_once()

    def test_schedules_job_with_correct_interval(self, all_mocks):
        all_mocks['bot_repo'].get.return_value = _make_bot(interval=5)

        start_scalping.main(['--bot-id', 'btc_1m_001'], standalone_mode=False)

        all_mocks['scheduler'].add_job.assert_called_once()
        kwargs = all_mocks['scheduler'].add_job.call_args.kwargs
        assert kwargs['minute'] == '*/5'

    def test_schedules_job_with_wildcard_for_1m_interval(self, all_mocks):
        all_mocks['bot_repo'].get.return_value = _make_bot(interval=1)

        start_scalping.main(['--bot-id', 'btc_1m_001'], standalone_mode=False)

        kwargs = all_mocks['scheduler'].add_job.call_args.kwargs
        assert kwargs['minute'] == '*'

    # --- Cron scheduling for larger intervals ---

    def test_schedules_hourly_interval(self, all_mocks):
        all_mocks['bot_repo'].get.return_value = _make_bot(interval=60)

        start_scalping.main(['--bot-id', 'btc_1m_001'], standalone_mode=False)

        kwargs = all_mocks['scheduler'].add_job.call_args.kwargs
        assert kwargs['minute'] == '0'
        assert 'hour' not in kwargs  # every hour, no hour constraint

    def test_schedules_4h_interval(self, all_mocks):
        all_mocks['bot_repo'].get.return_value = _make_bot(interval=240)

        start_scalping.main(['--bot-id', 'btc_1m_001'], standalone_mode=False)

        kwargs = all_mocks['scheduler'].add_job.call_args.kwargs
        assert kwargs['minute'] == '0'
        assert kwargs['hour'] == '*/4'

    def test_schedules_daily_interval(self, all_mocks):
        all_mocks['bot_repo'].get.return_value = _make_bot(interval=1440)

        start_scalping.main(['--bot-id', 'btc_1m_001'], standalone_mode=False)

        kwargs = all_mocks['scheduler'].add_job.call_args.kwargs
        assert kwargs['minute'] == '0'
        assert kwargs['hour'] == '0'

    def test_schedules_weekly_interval(self, all_mocks):
        all_mocks['bot_repo'].get.return_value = _make_bot(interval=10080)

        start_scalping.main(['--bot-id', 'btc_1m_001'], standalone_mode=False)

        kwargs = all_mocks['scheduler'].add_job.call_args.kwargs
        assert kwargs['minute'] == '0'
        assert kwargs['hour'] == '0'
        assert kwargs['day_of_week'] == '0'

    def test_schedules_monthly_interval(self, all_mocks):
        all_mocks['bot_repo'].get.return_value = _make_bot(interval=21600)

        start_scalping.main(['--bot-id', 'btc_1m_001'], standalone_mode=False)

        kwargs = all_mocks['scheduler'].add_job.call_args.kwargs
        assert kwargs['minute'] == '0'
        assert kwargs['hour'] == '0'
        assert kwargs['day'] == '1,16'

    def test_starts_scheduler(self, all_mocks):
        all_mocks['bot_repo'].get.return_value = _make_bot()

        start_scalping.main(['--bot-id', 'btc_1m_001'], standalone_mode=False)

        all_mocks['scheduler'].start.assert_called_once()

    def test_registers_signal_handlers(self, all_mocks):
        all_mocks['bot_repo'].get.return_value = _make_bot()

        start_scalping.main(['--bot-id', 'btc_1m_001'], standalone_mode=False)

        # signal.signal is called with the patched SIGTERM/SIGINT constants
        calls = all_mocks['signal'].signal.call_args_list
        registered_signals = {c.args[0] for c in calls}
        assert all_mocks['signal'].SIGTERM in registered_signals
        assert all_mocks['signal'].SIGINT in registered_signals

    # --- Dry run ---

    def test_dry_run_flag_passed_to_executor(self, all_mocks):
        all_mocks['bot_repo'].get.return_value = _make_bot()

        start_scalping.main(['--bot-id', 'btc_1m_001', '--dry-run'], standalone_mode=False)

        call_args = all_mocks['trade_executor_cls'].call_args
        assert call_args.kwargs['dry_run'] is True

    # --- Bot not found ---

    def test_aborts_when_bot_not_found(self, all_mocks):
        all_mocks['bot_repo'].get.return_value = None

        start_scalping.main(['--bot-id', 'unknown_bot'], standalone_mode=False)

        all_mocks['trade_executor_cls'].assert_not_called()
        all_mocks['scheduler'].start.assert_not_called()

    # --- Multiple bots ---

    def test_creates_executors_for_multiple_bots(self, all_mocks):
        bot_a = _make_bot('bot_a', interval=1)
        bot_b = _make_bot('bot_b', interval=5)
        all_mocks['bot_repo'].get.side_effect = [bot_a, bot_b]

        start_scalping.main(['--bot-id', 'bot_a', '--bot-id', 'bot_b'], standalone_mode=False)

        assert all_mocks['trade_executor_cls'].call_count == 2
        assert all_mocks['scheduler'].add_job.call_count == 2

    def test_aborts_without_creating_executors_when_any_bot_missing(self, all_mocks):
        '''If the second bot ID is invalid, no executors should be created — prevents orphaned runs.'''
        bot = _make_bot('valid_bot')
        all_mocks['bot_repo'].get.side_effect = [bot, None]

        start_scalping.main(['--bot-id', 'valid_bot', '--bot-id', 'missing'], standalone_mode=False)

        all_mocks['trade_executor_cls'].assert_not_called()
        all_mocks['scheduler'].start.assert_not_called()

    def test_aborts_when_first_bot_missing_even_if_second_valid(self, all_mocks):
        bot = _make_bot('valid_bot')
        all_mocks['bot_repo'].get.side_effect = [None, bot]

        start_scalping.main(['--bot-id', 'missing', '--bot-id', 'valid_bot'], standalone_mode=False)

        all_mocks['trade_executor_cls'].assert_not_called()
        all_mocks['scheduler'].start.assert_not_called()

    # --- Strategy creation ---

    def test_creates_strategy_with_bot_params(self, all_mocks):
        bot = _make_bot()
        all_mocks['bot_repo'].get.return_value = bot

        start_scalping.main(['--bot-id', 'btc_1m_001'], standalone_mode=False)

        all_mocks['create_strategy'].assert_called_once_with(bot.strategy_name, bot.parameters)

    # --- Scheduler job config ---

    def test_scheduler_job_uses_cron_trigger(self, all_mocks):
        all_mocks['bot_repo'].get.return_value = _make_bot()
        executor = all_mocks['trade_executor_cls'].return_value

        start_scalping.main(['--bot-id', 'btc_1m_001'], standalone_mode=False)

        args = all_mocks['scheduler'].add_job.call_args
        assert args.args[0] is executor.execute_interval
        assert args.args[1] == 'cron'

    def test_scheduler_job_has_5s_offset(self, all_mocks):
        all_mocks['bot_repo'].get.return_value = _make_bot()

        start_scalping.main(['--bot-id', 'btc_1m_001'], standalone_mode=False)

        kwargs = all_mocks['scheduler'].add_job.call_args.kwargs
        assert kwargs['second'] == '5'

    def test_scheduler_job_prevents_overlapping_runs(self, all_mocks):
        all_mocks['bot_repo'].get.return_value = _make_bot()

        start_scalping.main(['--bot-id', 'btc_1m_001'], standalone_mode=False)

        kwargs = all_mocks['scheduler'].add_job.call_args.kwargs
        assert kwargs['max_instances'] == 1

    # --- Shutdown handler ---

    def test_shutdown_handler_calls_executor_shutdown(self, all_mocks):
        all_mocks['bot_repo'].get.return_value = _make_bot()
        executor = all_mocks['trade_executor_cls'].return_value

        start_scalping.main(['--bot-id', 'btc_1m_001'], standalone_mode=False)

        # Extract the registered shutdown handler
        sigterm_call = next(
            c for c in all_mocks['signal'].signal.call_args_list
            if c.args[0] is all_mocks['signal'].SIGTERM
        )
        shutdown_handler = sigterm_call.args[1]

        # Invoke the shutdown handler
        shutdown_handler(all_mocks['signal'].SIGTERM, None)

        executor.request_shutdown.assert_called_once()
        all_mocks['scheduler'].shutdown.assert_called_once_with(wait=True)
        executor.shutdown.assert_called_once()


@pytest.mark.scripts
@pytest.mark.start_scalping
class TestIntervalToCron:

    @pytest.mark.parametrize('interval, expected', [
        (1, {'minute': '*'}),
        (5, {'minute': '*/5'}),
        (15, {'minute': '*/15'}),
        (30, {'minute': '*/30'}),
        (60, {'minute': '0'}),
        (240, {'minute': '0', 'hour': '*/4'}),
        (1440, {'minute': '0', 'hour': '0'}),
        (10080, {'minute': '0', 'hour': '0', 'day_of_week': '0'}),
        (21600, {'minute': '0', 'hour': '0', 'day': '1,16'}),
    ])
    def test_returns_correct_cron_kwargs(self, interval: int, expected: dict):
        assert interval_to_cron(interval) == expected

    def test_raises_for_unsupported_interval(self):
        with pytest.raises(ValueError, match='Unsupported interval 7m'):
            interval_to_cron(7)
