from dataclasses import dataclass
from enum import Enum

import optuna
from questionary import Choice

from utils import OptunaConfig


class StudyDirection(str, Enum):
    ''' Optimisation direction for an Optuna study. '''
    MAXIMIZE = 'maximize'
    MINIMIZE = 'minimize'


@dataclass(frozen=True)
class StudySummary:
    '''
    Summary row for an Optuna study.

    Attributes:
        name (str): Optuna study name (unique within the storage).
        pair (str): Trading pair parsed from the study name. Empty for legacy
            or hand-renamed studies that don't match the canonical shape.
        strategy (str): Strategy class name parsed from the study name.
            Empty for non-conforming names.
        trial_count (int): Total trials recorded against the study.
        best_is (float | None): Best in-sample objective value, or ``None`` if
            the study has no completed trial yet.
        direction (StudyDirection): Optimisation direction.
    '''
    name: str
    pair: str
    strategy: str
    trial_count: int
    best_is: float | None
    direction: StudyDirection


def list_studies() -> list[StudySummary]:
    '''
    Return a :class:`StudySummary` for every Optuna study in storage.

    Pair and strategy are parsed from the study name's
    ``{Strategy}_{pair}_{YYYYMMDD-YYYYMMDD}`` shape; legacy or hand-renamed
    studies that don't match are returned with empty pair/strategy strings.
    '''
    storage = optuna.storages.RDBStorage(url=OptunaConfig.DB_URL)
    summaries = optuna.get_all_study_summaries(storage)
    return [_to_study_summary(summary) for summary in summaries]


def get_study_choices() -> list[Choice]:
    ''' Wrap :func:`list_studies` for interactive Questionary CLI prompts. '''
    return [
        Choice(title=f'{summary.name} {summary.trial_count}', value=summary.name)
        for summary in list_studies()
    ]


def _to_study_summary(summary: optuna.study.StudySummary) -> StudySummary:
    # Extract details from study name (Strategy_pair_yyymmdd-yyymmdd)
    name_parts = summary.study_name.rsplit('_', 2)
    strategy = name_parts[0] if len(name_parts) == 3 else ''
    pair = name_parts[1] if len(name_parts) == 3 else ''

    direction = (
        StudyDirection.MAXIMIZE
        if summary.direction == optuna.study.StudyDirection.MAXIMIZE
        else StudyDirection.MINIMIZE
    )
    best_is = summary.best_trial.value if summary.best_trial is not None else None

    return StudySummary(
        name=summary.study_name,
        pair=pair,
        strategy=strategy,
        trial_count=summary.n_trials,
        best_is=best_is,
        direction=direction,
    )
