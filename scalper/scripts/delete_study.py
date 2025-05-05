import click
import optuna


@click.command()
@click.option('--study', required=True, help='Study name (e.g. SmaStrategy_XXBTZGBP_20240101-20241231)')
def delete_study(study: str):
    db_url = (
        'postgresql://optuna_user:password@localhost:5432/optuna_db'
        '?application_name=optuna_worker'
    )
    storage = optuna.storages.RDBStorage(url=db_url)
    optuna.delete_study(study_name=study, storage=storage)
