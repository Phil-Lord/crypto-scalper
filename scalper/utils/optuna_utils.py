import optuna

from utils import OPTUNA_DB_URL


def get_study_names() -> list[str]:
    ''' Retrieve all study names from the Optuna postgres database. '''
    storage = optuna.storages.RDBStorage(url=OPTUNA_DB_URL)
    study_summaries = optuna.study.get_all_study_summaries(storage=storage)
    return [study.study_name for study in study_summaries]
