import click
import optuna


@click.command()
@click.option('--study', required=True, help='Study name (e.g. SmaStrategy_XXBTZGBP_20240101-20241231)')
def delete_study(study: str):
    db_url = ('postgresql://optuna_user:password@localhost:5432/optuna_db')
    storage = optuna.storages.RDBStorage(url=db_url)

    if study != 'l':
        optuna.delete_study(study_name=study, storage=storage)
        print(f'Study {study} deleted.')

    study_summaries = optuna.study.get_all_study_summaries(storage=storage)
    if study_summaries:
        for study in study_summaries:
            print(study.study_name)
    else:
        print('No studies found.')


if __name__ == '__main__':
    delete_study()
