import logging

import click

from trade_executor import TradeExecutor
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
def start_scalping(bot_id: str, dry_run: bool) -> None:
    pass


if __name__ == '__main__':
    start_scalping()
