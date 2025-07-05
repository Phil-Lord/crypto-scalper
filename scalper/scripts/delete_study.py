import optuna
import questionary

from utils import get_study_choices, OPTUNA_DB_URL


def delete_study():
    study_choices = get_study_choices()
    if not study_choices:
        print('No studies found.')
        return
    study_name = questionary.select('Select a study:', choices=study_choices).ask()
    storage = optuna.storages.RDBStorage(url=OPTUNA_DB_URL)
    optuna.delete_study(study_name=study_name, storage=storage)
    print(f'Study {study_name} deleted.')


if __name__ == '__main__':
    delete_study()
