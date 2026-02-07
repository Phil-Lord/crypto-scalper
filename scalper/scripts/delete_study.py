import logging

import optuna
from questionary import checkbox, confirm

from utils import load_env, LOG_FORMAT, get_study_choices, OPTUNA_DB_URL

load_env()
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def delete_study():
    study_choices = get_study_choices()
    if not study_choices:
        print('No studies found.')
        return

    selected_studies = checkbox("Select studies:", choices=study_choices).ask()
    count = len(selected_studies)
    confirm_delete = confirm(f'Delete {count} stud{'ies' if count > 1 else 'y'}?').ask()
    if not confirm_delete:
        print('Deletion cancelled.')
        return

    storage = optuna.storages.RDBStorage(url=OPTUNA_DB_URL)
    for study_name in selected_studies:
        optuna.delete_study(study_name=study_name, storage=storage)
        print(f'Study {study_name} deleted.')


if __name__ == '__main__':
    delete_study()
