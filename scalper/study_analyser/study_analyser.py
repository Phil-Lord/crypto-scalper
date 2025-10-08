import json

import optuna
import pandas as pd

from .study_plotter import StudyPlotter
from utils import OPTUNA_DB_URL


class StudyAnalyser:
    def __init__(self, study_name: str):
        self.study_name = study_name
        self.study = self._load_study()

    def _load_study(self) -> optuna.Study:
        storage = optuna.storages.RDBStorage(
            url=OPTUNA_DB_URL,
            engine_kwargs={
                'pool_pre_ping': True,
                'connect_args': {
                    'application_name': 'study_analyser',
                    'keepalives_idle': 30
                }
            }
        )
        return optuna.load_study(study_name=self.study_name, storage=storage)

    def describe(self) -> None:
        pruned_count = len([trial for trial in self.study.trials if trial.state ==
                            optuna.trial.TrialState.PRUNED])
        print(f'Study name: {self.study.study_name}')
        print(f'Number of trials: {len(self.study.trials)} ({pruned_count} pruned)')
        print(f'Best value: {self.study.best_value} (trial {self.study.best_trial.number})')
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
