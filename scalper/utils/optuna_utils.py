from sqlalchemy import text
import optuna
from questionary import Choice

from utils import OptunaConfig


def get_study_choices() -> list[Choice]:
    ''' Retrieve all study names and trial counts from the database as Questionary Choices. '''
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

    choices = []
    for study_name, n_trials in result:
        display_name = f'{study_name} {n_trials}'
        choices.append(Choice(title=display_name, value=study_name))
    return choices
