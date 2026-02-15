import logging
from typing import Any

import click

from trade_executor import TradeExecutor
from strategy_manager import create_strategy
from utils import load_env, LOG_FORMAT, get_kraken_pair, SMA_CONFIG, PRECISION_TREND_CONFIG

load_env()
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


@click.command()
@click.option('--pair', required=True, help='Trading pair (e.g. BTCGBP)')
@click.option('--interval', required=False, type=int, help='Interval (e.g. 1, 3, 5, 15, etc.)')
@click.option('--strategy_name', required=True, help='Strategy name (e.g. SmaStrategy)')
def start_scalping(pair: str, interval: int, strategy_name: str) -> None:
    params = get_params_for_strategy(strategy_name)
    if params is None:
        return
    strategy = create_strategy(strategy_name, params)
    executor = TradeExecutor(get_kraken_pair(pair), interval, strategy)
    executor.execute_interval()


def get_params_for_strategy(strategy_name: str) -> dict[str, Any]:
    if strategy_name == 'SmaStrategy':
        return SMA_CONFIG
    elif strategy_name == 'PrecisionTrendStrategy':
        return PRECISION_TREND_CONFIG
    logger.error(f'Unknown strategy name: {strategy_name}')
    return None


if __name__ == '__main__':
    start_scalping()
