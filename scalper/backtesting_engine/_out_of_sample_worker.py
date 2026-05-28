'''
Subprocess entry point for out-of-sample evaluation.

Invoked by the walk-forward UI as::

    python -m backtesting_engine._out_of_sample_worker '<json>'

where ``<json>`` is a JSON object matching :class:`OutOfSampleArgs`.
``PROGRESS`` / ``DONE`` lines go to stdout; human logs go to stderr.

Subprocess entry point, not library API — deliberately absent from
``backtesting_engine/__init__.py``.
'''
import json
import logging
import sys

from core import DONE, JsonEvaluationProgressCallback, emit
from utils import load_env, LOG_FORMAT

from .out_of_sample_evaluation import OutOfSampleArgs, evaluate_out_of_sample

load_env()
logging.basicConfig(level=logging.WARNING, format=LOG_FORMAT, stream=sys.stderr)


def main(raw_args: str) -> None:
    '''
    Reconstruct :class:`OutOfSampleArgs` from JSON, run the evaluation, and
    emit a ``DONE`` line once every parameter set has been evaluated.

    :param raw_args: JSON object matching :class:`OutOfSampleArgs`.
    '''
    args = OutOfSampleArgs(**json.loads(raw_args))
    callback = JsonEvaluationProgressCallback()
    evaluate_out_of_sample(
        study_name=args.study_name,
        num_sets=args.num_sets,
        start=args.start,
        end=args.end,
        n_workers=args.n_workers,
        progress_callback=callback,
    )
    emit(DONE, {'trials': callback.count})


if __name__ == '__main__':
    main(sys.argv[1])
