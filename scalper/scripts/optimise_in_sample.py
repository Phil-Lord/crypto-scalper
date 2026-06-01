import logging
import sys

import click

from backtesting_engine import run_in_sample_optimisation
from core import DONE, JsonTrialProgressCallback, emit
from utils import LOG_FORMAT, get_second_timestamp, load_env, parse_datetime

load_env()
logging.basicConfig(level=logging.WARNING, format=LOG_FORMAT, stream=sys.stderr)


@click.command()
@click.option('--pair', '-p', required=True, help='Trading pair (e.g. BTCGBP).')
@click.option('--strategy_name', '-sn', required=True, help='Strategy name (e.g. SmaStrategy).')
@click.option('--start', '-s', required=True, help='Start datetime (e.g. 2025-1-1-0-0-0).')
@click.option('--end', '-e', required=True, help='End datetime (e.g. 2025-4-1-0-0-0).')
@click.option('--n_trials', '-n', required=True, type=int, help='Number of Optuna trials.')
@click.option('--n_jobs', '-j', required=False, type=int, default=-1,
              help='Optuna concurrency. -1 uses all available cores.')
def optimise_in_sample(
    pair: str, strategy_name: str, start: str, end: str, n_trials: int, n_jobs: int
) -> None:
    ''' Run an in-sample Optuna parameter optimisation. Emits one JSON line per trial. '''
    run_in_sample_optimisation(
        pair=pair,
        strategy_name=strategy_name,
        start=get_second_timestamp(*parse_datetime(start)),
        end=get_second_timestamp(*parse_datetime(end)),
        n_trials=n_trials,
        n_jobs=n_jobs,
        progress_callback=JsonTrialProgressCallback(),
    )
    emit(DONE, {'trials': n_trials})


if __name__ == '__main__':
    optimise_in_sample()
