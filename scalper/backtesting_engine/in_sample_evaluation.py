'''
In-sample Optuna parameter optimisation orchestration.

Provides the entry point :func:`run_in_sample_optimisation` plus the typed IPC
contract (:class:`InSampleArgs`) shared by :func:`build_in_sample_command` and
the ``_in_sample_worker`` subprocess entry point.

Mirrors :mod:`backtesting_engine.out_of_sample_evaluation` — argv builder and
its receiving end live together.
'''
import json
import sys
from dataclasses import asdict, dataclass

from data_system import SQLAlchemyClient, SQLAlchemyTradeRepository
from strategy_manager import create_strategy
from utils import (
    get_kraken_pair,
    PRECISION_TREND_CONFIG,
    PRECISION_TREND_GRID,
    SMA_CONFIG,
    SMA_GRID,
)

from .backtesting_engine import BacktestingEngine
from .parameter_optimisation import OptunaCallback


@dataclass(frozen=True)
class InSampleArgs:
    '''
    Typed IPC contract for the in-sample worker subprocess.

    Constructed by :func:`build_in_sample_command` on the UI side, JSON-encoded
    across the process boundary, and reconstructed by ``_in_sample_worker`` on
    the other side.

    Attributes:
        pair (str): Trading pair (e.g. ``'BTCGBP'``).
        strategy_name (str): Strategy class name (e.g. ``'SmaStrategy'``).
        start (float): In-sample window start (Unix seconds).
        end (float): In-sample window end (Unix seconds).
        n_trials (int): Number of Optuna trials to run.
    '''
    pair: str
    strategy_name: str
    start: float
    end: float
    n_trials: int


def build_in_sample_command(
    pair: str,
    strategy_name: str,
    start: float,
    end: float,
    n_trials: int,
) -> list[str]:
    '''
    Build the argv to invoke the in-sample worker as
    ``python -m backtesting_engine._in_sample_worker '<json>'``.

    The single positional arg is :class:`InSampleArgs` JSON-encoded — the same
    dataclass the worker reconstructs on the other side, so producer and
    consumer share one schema. Used by ``ui.services.walk_forward`` to spawn
    worker subprocesses.

    :param start: Window start, Unix seconds.
    :param end: Window end, Unix seconds.
    '''
    args = InSampleArgs(
        pair=pair, strategy_name=strategy_name, start=start, end=end, n_trials=n_trials
    )
    return [
        sys.executable, '-m', 'backtesting_engine._in_sample_worker',
        json.dumps(asdict(args)),
    ]


def run_in_sample_optimisation(
    pair: str,
    strategy_name: str,
    start: float,
    end: float,
    n_trials: int,
    progress_callback: OptunaCallback | None = None,
) -> None:
    '''
    Orchestrate an in-sample Optuna parameter optimisation end-to-end.

    Resolves the strategy's default config + search grid, builds a
    ``BacktestingEngine`` over ``[start, end]``, and delegates to
    :meth:`BacktestingEngine.optimise_parameters`.

    :param pair: Trading pair (e.g. ``'BTCGBP'``).
    :param strategy_name: Strategy class name (e.g. ``'SmaStrategy'``).
    :param start: Window start, Unix seconds.
    :param end: Window end, Unix seconds.
    :param n_trials: Number of Optuna trials.
    :param progress_callback: Optional Optuna callback ``(study, trial) -> None``
        invoked after each trial. Entry points pick presentation; the library
        installs no default progress bar.
    '''
    params, grid = _get_strategy_configs(strategy_name)
    engine = _build_engine(pair, strategy_name, start, end, params)
    engine.optimise_parameters(
        grid, n_trials=n_trials, progress_callback=progress_callback,
    )


def _get_strategy_configs(strategy_name: str) -> tuple[dict, dict]:
    if strategy_name == 'SmaStrategy':
        return SMA_CONFIG, SMA_GRID
    if strategy_name == 'PrecisionTrendStrategy':
        return PRECISION_TREND_CONFIG, PRECISION_TREND_GRID
    raise ValueError(f'No default config found for strategy: {strategy_name}')


def _build_engine(
    pair: str, strategy_name: str, start: float, end: float, params: dict,
) -> BacktestingEngine:
    strategy = create_strategy(strategy_name, params)
    client = SQLAlchemyClient()
    repository = SQLAlchemyTradeRepository(client)
    return BacktestingEngine(
        get_kraken_pair(pair), strategy, repository, start, end,
        interval=1, vectorised=True,
    )
