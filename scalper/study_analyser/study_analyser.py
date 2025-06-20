import json

import optuna
from optuna.storages import RDBStorage
import pandas as pd

from utils import OPTUNA_DB_URL
from .study_plotter import StudyPlotter


class StudyAnalyser:
    def __init__(self, study_name: str):
        self.study_name = study_name
        self.study = self._load_study()

    def _load_study(self) -> None:
        storage = RDBStorage(
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
        print(f'Best params: {json.dumps(self.study.best_params, indent=2)}')

    def plot_optimisation_history(self) -> None:
        StudyPlotter.plot_optimisation_history(self.study)

    def plot_param_importances(self) -> None:
        StudyPlotter.plot_param_importances(self.study)

    def plot_params_vs_objective(self) -> None:
        StudyPlotter.plot_params_vs_objective(self.study)

    def export_trials_dataframe(self) -> pd.DataFrame:
        return self.study.trials_dataframe(attrs=('number', 'value', 'params'))
