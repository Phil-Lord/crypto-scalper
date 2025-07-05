import optuna
from questionary import Choice

from utils import OPTUNA_DB_URL


def get_study_choices() -> list[Choice]:
    ''' Retrieve all study names and trial counts from the database as Questionary Choices. '''
    storage = optuna.storages.RDBStorage(url=OPTUNA_DB_URL)
    study_summaries = optuna.study.get_all_study_summaries(storage=storage)

    choices = []
    for summary in study_summaries:
        display_name = f'{summary.study_name} {summary.n_trials}'
        choices.append(Choice(title=display_name, value=summary.study_name))
    return choices
