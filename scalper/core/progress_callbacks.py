'''
Progress callbacks that emit :data:`PROGRESS` JSON lines on the subprocess event stream.

Both the human-facing CLI scripts and the backtesting-engine worker entry
points wire one of these into a long-running optimisation or evaluation so the
parent process can render live progress. Errors and human logs are routed to
stderr by the entry point; only ``PROGRESS`` lines go to stdout.
'''
import optuna

from .event_stream import PROGRESS, emit


class JsonTrialProgressCallback:
    '''
    Optuna study callback that emits a single ``PROGRESS {...}`` JSON line per
    trial to stdout. Used by the in-sample parameter optimisation.
    '''

    def __call__(self, study: optuna.study.Study, trial: optuna.trial.FrozenTrial) -> None:
        best = study.best_value if self._has_completed_trial(study) else None
        emit(PROGRESS, {
            'trial': trial.number,
            'value': trial.value,
            'best': best,
        })

    def _has_completed_trial(self, study: optuna.study.Study) -> bool:
        ''' Returns True if the study has at least one completed trial. '''
        return any(
            t.state == optuna.trial.TrialState.COMPLETE for t in study.get_trials(deepcopy=False)
        )


class JsonEvaluationProgressCallback:
    '''
    ``() -> None`` tick callback that emits a single ``PROGRESS {...}`` JSON
    line per parameter set evaluated. Used by the out-of-sample evaluation.

    Attributes:
        count (int): Number of parameter sets evaluated so far — also the
            number of ``PROGRESS`` lines emitted.
    '''

    def __init__(self) -> None:
        self.count = 0

    def __call__(self) -> None:
        self.count += 1
        emit(PROGRESS, {'trial': self.count})
