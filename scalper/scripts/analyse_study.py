import optuna
import questionary

from utils import OPTUNA_DB_URL
from study_analyser import StudyAnalyser


def analyse_study() -> None:
    study_names = get_study_names()
    if not study_names:
        print("No studies found.")
        return
    study_name = questionary.select("Select a study:", choices=study_names).ask()

    analyser = StudyAnalyser(study_name)
    analyser.describe()
    analyser.plot_optimisation_history()
    analyser.plot_param_importances()
    analyser.plot_params_vs_objective()
    print(analyser.export_trials_dataframe())


def get_study_names() -> list[str]:
    storage = optuna.storages.RDBStorage(url=OPTUNA_DB_URL)
    study_summaries = optuna.study.get_all_study_summaries(storage=storage)
    return [study.study_name for study in study_summaries]


if __name__ == '__main__':
    analyse_study()
