import logging

import click

from data_system import (
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
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


@click.command()
@click.option(
    '--bot-id', required=True, multiple=True, type=str,
    help='Bot ID(s) to run (e.g. --bot-id bot1 --bot-id bot2)'
)
@click.option('--dry-run', is_flag=True, default=False, help='Run the bot in dry-run mode')
def start_scalping(bot_id: tuple[str, ...], dry_run: bool) -> None:
    client = SupabaseClient()
    bot_repository = SupabaseBotRepository(client)

    for id in bot_id:
        bot = bot_repository.get(id)
        if not bot:
            logger.error(f'Bot with ID {id} not found')
            continue

        strategy = create_strategy(bot.strategy_name, bot.parameters)
        sizer = AllInPositionSizer()
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

        executor.recover_state()
        executor.warm_up()


if __name__ == '__main__':
    start_scalping()
