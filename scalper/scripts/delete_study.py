import optuna
import questionary

from utils import get_study_names, OPTUNA_DB_URL


def delete_study():
    study_names = get_study_names()
    if not study_names:
        print('No studies found.')
        return
    study_name = questionary.select('Select a study:', choices=study_names).ask()
    storage = optuna.storages.RDBStorage(url=OPTUNA_DB_URL)
    optuna.delete_study(study_name=study_name, storage=storage)
    print(f'Study {study_name} deleted.')


if __name__ == '__main__':
    delete_study()
