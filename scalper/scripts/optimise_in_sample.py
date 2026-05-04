import json
import logging
import sys

import click
import optuna

from backtesting_engine import BacktestingEngine
from data_system import SQLAlchemyClient, SQLAlchemyTradeRepository
from strategy_manager import create_strategy
from utils import (
    load_env,
    LOG_FORMAT,
    get_kraken_pair,
    get_second_timestamp,
    parse_datetime,
    SMA_GRID,
    PRECISION_TREND_GRID,
    SMA_CONFIG,
    PRECISION_TREND_CONFIG,
)

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
    params, grid = get_strategy_configs(strategy_name)
    engine = build_engine(pair, strategy_name, start, end, params)
    callback = JsonProgressCallback()
    engine.optimise_parameters(grid, n_trials=n_trials, n_jobs=n_jobs, progress_callback=callback)
    emit('DONE', {'trials': n_trials})


def get_strategy_configs(strategy_name: str) -> tuple[dict, dict]:
    if strategy_name == 'SmaStrategy':
        return SMA_CONFIG, SMA_GRID
    if strategy_name == 'PrecisionTrendStrategy':
        return PRECISION_TREND_CONFIG, PRECISION_TREND_GRID
    raise ValueError(f'No default config found for strategy: {strategy_name}')


def build_engine(
    pair: str, strategy_name: str, start: str, end: str, params: dict
) -> BacktestingEngine:
    kraken_pair = get_kraken_pair(pair)
    strategy = create_strategy(strategy_name, params)
    client = SQLAlchemyClient()
    repository = SQLAlchemyTradeRepository(client)
    start_ts = get_second_timestamp(*parse_datetime(start))
    end_ts = get_second_timestamp(*parse_datetime(end))
    return BacktestingEngine(
        kraken_pair, strategy, repository, start_ts, end_ts, interval=1, vectorised=True,
    )


class JsonProgressCallback:
    '''
    Optuna callback that emits a single ``PROGRESS {...}`` JSON line per trial
    to stdout. Errors and human logs are routed to stderr by the entry point.
    '''

    def __call__(self, study: optuna.study.Study, trial: optuna.trial.FrozenTrial) -> None:
        best = study.best_value if self._has_completed_trial(study) else None
        emit('PROGRESS', {
            'trial': trial.number,
            'value': trial.value,
            'best': best,
        })

    def _has_completed_trial(self, study: optuna.study.Study) -> bool:
        ''' Returns True if the study has at least one completed trial. '''
        return any(
            t.state == optuna.trial.TrialState.COMPLETE for t in study.get_trials(deepcopy=False)
        )


def emit(event: str, payload: dict) -> None:
    ''' Emit a JSON line to stdout with the given event name and payload. '''
    sys.stdout.write(f'{event} {json.dumps(payload)}\n')
    sys.stdout.flush()


if __name__ == '__main__':
    optimise_in_sample()
