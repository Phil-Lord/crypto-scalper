from datetime import timezone
import logging
import os
import signal
from types import FrameType

from apscheduler.schedulers.blocking import BlockingScheduler
import click

from data_system import (
    Bot,
    SupabaseClient,
    SupabaseBotRepository,
    SupabaseBotOrderRepository,
    SupabaseBotRunRepository,
    SupabaseBotTickRepository
)
from exchange_connector import (
    AddOrderConnector,
    BalanceConnector,
    OhlcConnector,
    QueryOrdersConnector
)
from trade_executor import AllInPositionSizer, TradeExecutor
from strategy_manager import create_strategy
from utils import load_env, LOG_FORMAT

load_env()

# Default log level is WARNING to reduce noise from httpcore, hpack, etc.
logging.basicConfig(level=logging.WARNING, format=LOG_FORMAT)

# Application log level is set from env var, defaulting to INFO
app_level = os.getenv('LOG_LEVEL', 'INFO').upper()
for name in ('trade_executor', 'exchange_connector', 'data_system', 'strategy_manager', 'scripts'):
    logging.getLogger(name).setLevel(app_level)

logger = logging.getLogger(__name__)

INTERVAL_CRON_MAP: dict[int, dict[str, str]] = {
    1: {'minute': '*'},
    5: {'minute': '*/5'},
    15: {'minute': '*/15'},
    30: {'minute': '*/30'},
    60: {'minute': '0'},
    240: {'minute': '0', 'hour': '*/4'},
    1440: {'minute': '0', 'hour': '0'},
    10080: {'minute': '0', 'hour': '0', 'day_of_week': '0'},
    21600: {'minute': '0', 'hour': '0', 'day': '1,16'},
}


@click.command()
@click.option(
    '--bot-id', required=True, multiple=True, type=str,
    help='Bot ID(s) to run (e.g. --bot-id bot1 --bot-id bot2)'
)
@click.option('--dry-run', is_flag=True, default=False, help='Run the bot in dry-run mode')
def start_scalping(bot_id: tuple[str, ...], dry_run: bool) -> None:
    bot_repository = SupabaseBotRepository(SupabaseClient())

    # Validate all bot IDs before initialising any executors
    bots: list[Bot] = []
    for id in bot_id:
        bot = bot_repository.get(id)
        if not bot:
            logger.error(f'Bot with ID {id} not found, aborting')
            return
        bots.append(bot)

    executors: list[TradeExecutor] = []
    scheduler = BlockingScheduler(timezone=timezone.utc)

    for bot in bots:
        strategy = create_strategy(bot.strategy_name, bot.parameters)
        sizer = AllInPositionSizer()
        client = SupabaseClient()
        executor = TradeExecutor(
            bot,
            strategy,
            sizer,
            SupabaseBotRunRepository(client),
            SupabaseBotTickRepository(client),
            SupabaseBotOrderRepository(client),
            BalanceConnector(),
            OhlcConnector(),
            AddOrderConnector(),
            QueryOrdersConnector(),
            dry_run=dry_run
        )

        executor.warm_up()
        executor.recover_state()
        executors.append(executor)

        cron_kwargs = interval_to_cron(bot.interval)
        scheduler.add_job(
            executor.execute_interval,
            'cron',                         # wall-clock-aligned trigger
            **cron_kwargs,                  # e.g. minute='*/5' for 5m, hour='*/4' for 4h interval
            second='5',                     # fire 5s into the minute (Kraken data lag)
            jitter=3,                       # stagger multi-bot calls by up to ±3s
            misfire_grace_time=1,           # discard if >1s late; prevents stale catch-up runs
            max_instances=1,                # prevent overlapping runs for this bot
        )

    def _shutdown(signum: int, frame: FrameType | None) -> None:
        for executor in executors:
            executor.request_shutdown()
        scheduler.shutdown(wait=True)
        for executor in executors:
            executor.shutdown()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    scheduler.start()


def interval_to_cron(interval: int) -> dict[str, str]:
    '''
    Converts a bot interval (in minutes) to APScheduler cron keyword arguments.

    APScheduler's cron minute field only supports 0-59, so intervals >= 60
    must be expressed using hour/day_of_week fields instead.

    :param interval: OHLC interval in minutes (must be a valid Kraken interval).
    :return: Dict of cron trigger kwargs (minute, hour, etc.).
    :raises ValueError: If the interval is not supported for scheduling.
    '''
    cron_kwargs = INTERVAL_CRON_MAP.get(interval)
    if cron_kwargs is None:
        raise ValueError(
            f'Unsupported interval {interval}m for cron scheduling. '
            f'Supported: {sorted(INTERVAL_CRON_MAP)}'
        )
    return cron_kwargs


if __name__ == '__main__':
    start_scalping()
