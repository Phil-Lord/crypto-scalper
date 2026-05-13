import logging
import sys

import click

from backtesting_engine import evaluate_out_of_sample as run_evaluate_out_of_sample
from core import DONE, PROGRESS, emit
from utils import load_env, LOG_FORMAT, get_second_timestamp, parse_datetime

load_env()
logging.basicConfig(level=logging.WARNING, format=LOG_FORMAT, stream=sys.stderr)


def build_command(
    study_name: str,
    num_sets: int,
    start: str,
    end: str,
    n_workers: int = 1,
) -> list[str]:
    '''
    Build the argv to invoke this script as ``python -m scripts.evaluate_out_of_sample``.

    Colocated with the click options so flag changes update one place. Used by
    ``ui.services.walk_forward`` to spawn the evaluation subprocess.
    '''
    return [
        sys.executable, '-m', 'scripts.evaluate_out_of_sample',
        '-sn', study_name,
        '-n', str(num_sets),
        '-s', start,
        '-e', end,
        '-w', str(n_workers),
    ]


@click.command()
@click.option('--study_name', '-sn', required=True, help='Optuna study name.')
@click.option('--num_sets', '-n', required=True, type=int,
              help='Number of top parameter sets to evaluate.')
@click.option('--start', '-s', required=True, help='Start datetime (e.g. 2025-4-1-0-0-0).')
@click.option('--end', '-e', required=True, help='End datetime (e.g. 2025-7-1-0-0-0).')
@click.option('--n_workers', '-w', required=False, type=int, default=1,
              help='Number of worker processes (>1 enables ProcessPoolExecutor).')
def evaluate_out_of_sample(
    study_name: str, num_sets: int, start: str, end: str, n_workers: int
) -> None:
    ''' Evaluate top parameter sets on an out-of-sample window. Emits JSON progress lines. '''
    start_ts = get_second_timestamp(*parse_datetime(start))
    end_ts = get_second_timestamp(*parse_datetime(end))

    callback = JsonProgressCallback()
    run_evaluate_out_of_sample(
        study_name=study_name,
        num_sets=num_sets,
        start=start_ts,
        end=end_ts,
        n_workers=n_workers,
        progress_callback=callback,
    )
    emit(DONE, {'trials': callback.count})


class JsonProgressCallback:
    '''
    ``() -> None`` tick callback that emits a single ``PROGRESS {...}`` JSON line
    per parameter set evaluated. Errors and human logs go to stderr.
    '''

    def __init__(self) -> None:
        self.count = 0

    def __call__(self) -> None:
        self.count += 1
        emit(PROGRESS, {'trial': self.count})


if __name__ == '__main__':
    evaluate_out_of_sample()
