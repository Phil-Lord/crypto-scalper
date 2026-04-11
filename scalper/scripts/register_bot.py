import click

from data_system import Bot, BotRepository


@click.command()
@click.option('-i', '--id', required=True, help='Unique identifier for the bot')
@click.option('-p', '--pair', required=True, help='Trading pair in Kraken format (e.g. XXBTZGBP)')
@click.option('-sn', '--strategy-name', required=True, help='Strategy name (e.g. SmaStrategy)')
@click.option('-sv', '--strategy-version', required=True, help='Strategy version (record-keeping metadata, not used functionally)')
@click.option('-int', '--interval', required=True, type=int, help='Interval (e.g. 1, 3, 5, 15, etc.)')
@click.option('-par', '--parameters', required=True, help='Strategy parameters (JSON string)')
def register_bot(
        id: str,
        pair: str,
        strategy_name: str,
        strategy_version: str,
        interval: int,
        parameters: str
) -> None:
    bot_repository = BotRepository()
    added_bot = bot_repository.add(
        Bot(id, pair, strategy_name, strategy_version, interval, parameters)
    )
    click.echo(f'Bot registered successfully: {added_bot}')


if __name__ == '__main__':
    register_bot()
