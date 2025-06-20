import questionary

from study_analyser import StudyAnalyser
from utils import get_study_names


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


if __name__ == '__main__':
    analyse_study()
