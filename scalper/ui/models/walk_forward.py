from dataclasses import dataclass
from enum import Enum


class StudyDirection(str, Enum):
    ''' Optimisation direction for an Optuna study. '''
    MAXIMIZE = 'maximize'
    MINIMIZE = 'minimize'


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
