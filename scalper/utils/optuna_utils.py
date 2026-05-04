from dataclasses import dataclass

from sqlalchemy import text
import optuna
from questionary import Choice

from utils import OptunaConfig


@dataclass(frozen=True)
class StudySummary:
    '''
    Summary of an Optuna study, suitable for non-interactive listing.

    Attributes:
        study_name (str): The Optuna study name (unique within the storage).
        n_trials (int): Total number of trials recorded against the study.
    '''
    study_name: str
    n_trials: int


def list_studies() -> list[StudySummary]:
    ''' Retrieve all studies from the Optuna storage as plain summaries. '''
    storage = optuna.storages.RDBStorage(url=OptunaConfig.DB_URL)
    engine = storage.engine

    query = text(
        """
        SELECT s.study_name, COUNT(t.trial_id) AS n_trials
        FROM studies s
        LEFT JOIN trials t ON s.study_id = t.study_id
        GROUP BY s.study_name
        ORDER BY n_trials
        """
    )

    with engine.connect() as connection:
        result = connection.execute(query).fetchall()

    return [StudySummary(study_name=name, n_trials=n) for name, n in result]


def get_study_choices() -> list[Choice]:
    ''' Wrap :func:`list_studies` for interactive Questionary CLI prompts. '''
    return [
        Choice(title=f'{summary.study_name} {summary.n_trials}', value=summary.study_name)
        for summary in list_studies()
    ]
