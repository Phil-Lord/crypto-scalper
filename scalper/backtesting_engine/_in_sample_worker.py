'''
Subprocess entry point for in-sample Optuna parameter optimisation.

Invoked by the walk-forward UI as::

    python -m backtesting_engine._in_sample_worker '<json>'

where ``<json>`` is a JSON object matching :class:`InSampleArgs`.
``PROGRESS`` / ``DONE`` lines go to stdout; human logs go to stderr.

Subprocess entry point, not library API — deliberately absent from
``backtesting_engine/__init__.py``.
'''
import json
import logging
import sys

from core import DONE, JsonTrialProgressCallback, emit
from utils import load_env, LOG_FORMAT

from .in_sample_evaluation import InSampleArgs, run_in_sample_optimisation

load_env()
logging.basicConfig(level=logging.WARNING, format=LOG_FORMAT, stream=sys.stderr)


def main(raw_args: str) -> None:
    '''
    Reconstruct :class:`InSampleArgs` from JSON, run the optimisation, and
    emit a ``DONE`` line once every trial has completed.

    :param raw_args: JSON object matching :class:`InSampleArgs`.
    '''
    args = InSampleArgs(**json.loads(raw_args))
    run_in_sample_optimisation(
        pair=args.pair,
        strategy_name=args.strategy_name,
        start=args.start,
        end=args.end,
        n_trials=args.n_trials,
        n_jobs=args.n_jobs,
        progress_callback=JsonTrialProgressCallback(),
    )
    emit(DONE, {'trials': args.n_trials})


if __name__ == '__main__':
    main(sys.argv[1])
