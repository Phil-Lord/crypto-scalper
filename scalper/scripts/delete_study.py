import click
import optuna

from utils import get_study_names, OPTUNA_DB_URL


@click.command()
@click.option('--study', required=True, help='Study name (e.g. SmaStrategy_XXBTZGBP_20240101-20241231)')
def delete_study(study: str):
    storage = optuna.storages.RDBStorage(url=OPTUNA_DB_URL)

    if study != 'l':
        optuna.delete_study(study_name=study, storage=storage)
        print(f'Study {study} deleted.')

    study_names = get_study_names()
    if study_names:
        for name in study_names:
            print(name)
    else:
        print("No studies found.")


if __name__ == '__main__':
    delete_study()
