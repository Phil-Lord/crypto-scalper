import json
import logging

import click

from data_system import Bot, SupabaseBotRepository, SupabaseClient
from utils import LOG_FORMAT, load_env

load_env()
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


@click.command()
@click.option('-i', '--id', 'bot_id', required=True, help='Unique identifier for the bot')
@click.option('-p', '--pair', required=True, help='Trading pair in Kraken format (e.g. XXBTZGBP)')
@click.option('-sn', '--strategy-name', required=True, help='Strategy name (e.g. SmaStrategy)')
@click.option('-sv', '--strategy-version', required=True, help='Strategy version (record-keeping metadata, not used functionally)')
@click.option('-int', '--interval', required=True, type=int, help='Interval (e.g. 1, 3, 5, 15, etc.)')
@click.option('-par', '--parameters', required=True, help='Strategy parameters (JSON string)')
def register_bot(
        bot_id: str,
        pair: str,
        strategy_name: str,
        strategy_version: str,
        interval: int,
        parameters: str
) -> None:
    parsed_parameters = json.loads(parameters)
    bot_repository = SupabaseBotRepository(SupabaseClient())
    added_bot = bot_repository.add(
        Bot(
            id=bot_id,
            pair=pair,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            interval=interval,
            parameters=parsed_parameters
        )
    )
    click.echo(f'Bot registered successfully: {added_bot}')


if __name__ == '__main__':
    register_bot()
