'''
Subprocess entry point for in-sample Optuna parameter optimisation.

Invoked by the walk-forward UI as::

    python -m backtesting_engine._in_sample_worker '<json>'

where ``<json>`` is a JSON object with keys ``pair``, ``strategy_name``,
``start`` and ``end`` (Unix-second timestamps), ``n_trials`` and ``n_jobs``.
``PROGRESS`` / ``DONE`` lines go to stdout; human logs go to stderr.

This is a subprocess entry point, not library API — deliberately absent from
``backtesting_engine/__init__.py``.
'''
import json
import logging
import sys

from core import DONE, JsonTrialProgressCallback, emit
from data_system import SQLAlchemyClient, SQLAlchemyTradeRepository
from strategy_manager import create_strategy
from utils import (
    load_env,
    LOG_FORMAT,
    get_kraken_pair,
    SMA_GRID,
    PRECISION_TREND_GRID,
    SMA_CONFIG,
    PRECISION_TREND_CONFIG,
)

from .backtesting_engine import BacktestingEngine

load_env()
logging.basicConfig(level=logging.WARNING, format=LOG_FORMAT, stream=sys.stderr)


def main(raw_args: str) -> None:
    '''
    Run the optimisation described by the JSON-encoded ``raw_args`` and emit a
    ``DONE`` line once every trial has completed.

    :param raw_args: JSON object with keys
        ``pair``, ``strategy_name``, ``start``, ``end``, ``n_trials`` and ``n_jobs``.
    '''
    args = json.loads(raw_args)
    params, grid = _get_strategy_configs(args['strategy_name'])
    engine = _build_engine(
        args['pair'], args['strategy_name'], args['start'], args['end'], params
    )
    engine.optimise_parameters(
        grid,
        n_trials=args['n_trials'],
        n_jobs=args['n_jobs'],
        progress_callback=JsonTrialProgressCallback(),
    )
    emit(DONE, {'trials': args['n_trials']})


def _get_strategy_configs(strategy_name: str) -> tuple[dict, dict]:
    if strategy_name == 'SmaStrategy':
        return SMA_CONFIG, SMA_GRID
    if strategy_name == 'PrecisionTrendStrategy':
        return PRECISION_TREND_CONFIG, PRECISION_TREND_GRID
    raise ValueError(f'No default config found for strategy: {strategy_name}')


def _build_engine(
    pair: str, strategy_name: str, start: float, end: float, params: dict
) -> BacktestingEngine:
    strategy = create_strategy(strategy_name, params)
    client = SQLAlchemyClient()
    repository = SQLAlchemyTradeRepository(client)
    return BacktestingEngine(
        get_kraken_pair(pair), strategy, repository, start, end,
        interval=1, vectorised=True,
    )


if __name__ == '__main__':
    main(sys.argv[1])
