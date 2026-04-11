import logging
import os
import signal

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
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'), format=LOG_FORMAT)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


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
    scheduler = BlockingScheduler()

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

        minute_expr = '*' if bot.interval == 1 else f'*/{bot.interval}'
        scheduler.add_job(
            executor.execute_interval,
            'cron',                         # wall-clock-aligned trigger
            minute=minute_expr,             # respects bot interval (e.g. */5 for 5m)
            second='5',                     # fire 5s into the minute (Kraken data lag)
            jitter=3,                       # stagger multi-bot calls by up to ±3s
            misfire_grace_time=1,           # discard if >1s late; prevents stale catch-up runs
            max_instances=1,                # prevent overlapping runs for this bot
        )

    def _shutdown(signum, frame):
        for executor in executors:
            executor.request_shutdown()
        scheduler.shutdown(wait=True)
        for executor in executors:
            executor.shutdown()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    scheduler.start()


if __name__ == '__main__':
    start_scalping()
