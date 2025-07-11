import json
import subprocess

import optuna
import pandas as pd

from .study_plotter import StudyPlotter
from utils import OPTUNA_DB_URL


class StudyAnalyser:
    def __init__(self, study_name: str):
        self.study_name = study_name
        self.study = self._load_study()

    def _load_study(self) -> None:
        storage = optuna.storages.RDBStorage(
            url=OPTUNA_DB_URL,
            engine_kwargs={
                'pool_pre_ping': True,
                'connect_args': {
                    'application_name': 'analysis_script',
                    'keepalives_idle': 30
                }
            }
        )
        return optuna.load_study(study_name=self.study_name, storage=storage)

    def describe(self) -> None:
        print(f'Study name: {self.study.study_name}')
        print(f'Number of trials: {len(self.study.trials)}')
        print(f'Best value: {self.study.best_value}')
        print(f'Best params: {json.dumps(self.study.best_params, indent=4).replace('"', "'")}')

    def describe_trial_by_number(self, trial_number: int) -> None:
        trial = self.study.trials[trial_number]
        print(f'Number: {trial.number}/{len(self.study.trials)}')
        print(f'Value: {trial.value}')
        print(f'Params: {json.dumps(trial.params, indent=4).replace('"', "'")}')

    def export_trials_dataframe(self) -> pd.DataFrame:
        return self.study.trials_dataframe(attrs=('number', 'value', 'params'))

    def plot_hyperparameter_correlation_matrix(self):
        StudyPlotter.plot_hyperparameter_correlation_matrix(self.study)

    def plot_parameter_stability(self):
        StudyPlotter.plot_parameter_stability(self.study)

    def launch_dashboard(self) -> None:
        url = OPTUNA_DB_URL.replace('postgresql://', 'postgresql+psycopg2://')
        print('Launching Optuna dashboard at http://localhost:8080 ...')
        subprocess.run(['optuna-dashboard', url])
