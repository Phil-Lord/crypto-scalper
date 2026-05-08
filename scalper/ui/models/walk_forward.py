from dataclasses import dataclass
from enum import Enum


class StudyDirection(str, Enum):
    ''' Optimisation direction for an Optuna study. '''
    MAXIMIZE = 'maximize'
    MINIMIZE = 'minimize'


class TrialVerdict(str, Enum):
    '''
    Generalisation verdict for a trial against an OOS window.

    ``PENDING`` — trial has no OOS evaluation in the chosen window yet.
    ``GENERALISES`` — OOS geo-mean return at or above ``OOS_OVERFIT_THRESHOLD``.
    ``OVERFIT`` — OOS geo-mean return below ``OOS_OVERFIT_THRESHOLD``.
    '''
    PENDING = 'pending'
    GENERALISES = 'generalises'
    OVERFIT = 'overfit'


@dataclass(frozen=True)
class StudySummary:
    '''
    Summary row for the studies rail.

    Attributes:
        name (str): Optuna study name.
        pair (str): Trading pair parsed from the study name.
        strategy (str): Strategy class name parsed from the study name.
        trial_count (int): Total trials recorded against the study.
        best_is (float | None): Best in-sample objective value, or ``None`` if
            the study has no completed trial yet.
        direction (StudyDirection): Optimisation direction.

    Note:
        Does not include ``last_run_state`` — that is a UI concern merged in by
        the page from in-process state.
    '''
    name: str
    pair: str
    strategy: str
    trial_count: int
    best_is: float | None
    direction: StudyDirection


@dataclass(frozen=True)
class OosWindowSummary:
    '''
    Aggregate of OOS evaluations for a single (start, end) window.

    Attributes:
        start (float): Window start (Unix seconds).
        end (float): Window end (Unix seconds).
        best_oos (float): Highest geo-mean OOS return across evaluated trials.
        generalised_count (int): Trials with OOS at or above ``OOS_OVERFIT_THRESHOLD``.
        overfit_count (int): Trials with OOS below ``OOS_OVERFIT_THRESHOLD``.
    '''
    start: float
    end: float
    best_oos: float
    generalised_count: int
    overfit_count: int


@dataclass(frozen=True)
class TrialWithOos:
    '''
    Top-trial row joined with its OOS score for the selected window.

    Attributes:
        trial_number (int): Optuna trial number.
        is_value (float): In-sample objective value.
        oos_score (float | None): OOS geo-mean return for the chosen window, or
            ``None`` if the trial has not been evaluated in that window yet.
        delta (float | None): ``oos_score - is_value``;
            ``None`` when ``oos_score`` is ``None``.
        verdict (TrialVerdict): Pending / generalises / overfit.
        params (dict): Trial parameter dict (same shape as ``trial.params``).
    '''
    trial_number: int
    is_value: float
    oos_score: float | None
    delta: float | None
    verdict: TrialVerdict
    params: dict
