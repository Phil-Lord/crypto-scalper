import click
import optuna


@click.command()
@click.option('--study', required=True, help='Study name (e.g. SmaStrategy_XXBTZGBP_20240101-20241231)')
def delete_study(study: str):
    db_url = ('postgresql://optuna_user:password@localhost:5432/optuna_db')
    storage = optuna.storages.RDBStorage(url=db_url)
    optuna.delete_study(study_name=study, storage=storage)

    print('Study deleted. Remaining studies:')
    for study in optuna.study.get_all_study_summaries(storage=storage):
        print(study.study_name)


if __name__ == '__main__':
    delete_study()
