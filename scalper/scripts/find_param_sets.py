import logging

import click
import questionary

from backtesting_engine import find_params
from utils import LOG_FORMAT, get_study_choices, get_second_timestamp, parse_datetime

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


@click.command()
@click.option('--num_sets', '-n', required=True, type=int, help='Number of top parameter sets.')
@click.option('--start', '-s', required=True, help='Start datetime.')
@click.option('--end', '-e', required=True, help='End datetime.')
def find_param_sets(num_sets: int, start: str, end: str) -> None:
    study_choices = get_study_choices()
    if not study_choices:
        print('No studies found.')
        return
    study_name = questionary.select('Select a study:', choices=study_choices).ask()

    start = get_second_timestamp(*parse_datetime(start))
    end = get_second_timestamp(*parse_datetime(end))

    find_params(study_name, num_sets, start, end)


if __name__ == '__main__':
    find_param_sets()
