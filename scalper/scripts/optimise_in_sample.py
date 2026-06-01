import logging
import sys

import click

from backtesting_engine import run_in_sample_optimisation, run_in_sample_workers
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
@click.option('--n_workers', '-w', required=False, type=int, default=1,
              help='Number of worker subprocesses. >1 splits trials across OS processes.')
def optimise_in_sample(
    pair: str, strategy_name: str, start: str, end: str, n_trials: int, n_workers: int
) -> None:
    '''
    Run an in-sample Optuna parameter optimisation. Emits one JSON line per trial.

    With n_workers > 1, trials are split across n_workers subprocesses,
    all contributing to the same Optuna study via Postgres.
    '''
    start_ts = get_second_timestamp(*parse_datetime(start))
    end_ts = get_second_timestamp(*parse_datetime(end))

    if n_workers == 1:
        run_in_sample_optimisation(
            pair=pair,
            strategy_name=strategy_name,
            start=start_ts,
            end=end_ts,
            n_trials=n_trials,
            progress_callback=JsonTrialProgressCallback(),
        )
        emit(DONE, {'trials': n_trials})
        return

    # Each worker emits its own PROGRESS / DONE lines,
    # so this path doesn't emit an aggregate DONE.
    run_in_sample_workers(
        pair=pair,
        strategy_name=strategy_name,
        start=start_ts,
        end=end_ts,
        n_trials=n_trials,
        n_workers=n_workers,
    )


if __name__ == '__main__':
    optimise_in_sample()
