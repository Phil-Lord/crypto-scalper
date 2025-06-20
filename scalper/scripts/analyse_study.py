import questionary

from study_analyser import StudyAnalyser
from utils import get_study_names


def analyse_study() -> None:
    study_names = get_study_names()
    if not study_names:
        print('No studies found.')
        return
    study_name = questionary.select('Select a study:', choices=study_names).ask()
    analyser = StudyAnalyser(study_name)
    run_analysis_dashboard(analyser)


def run_analysis_dashboard(analyser: StudyAnalyser) -> None:
    while True:
        action = questionary.select(
            'Select an action:',
            choices=[
                '📄 Describe Study',
                '📤 Export Trials DataFrame',
                '🧮 Plot Hyperparameter Correlation Matrix',
                '📊 Plot Parameter Stability',
                '📺 Launch Optuna HTML Dashboard',
                '❌ Quit'
            ]
        ).ask()

        if action == '📄 Describe Study':
            analyser.describe()
        elif action == '📤 Export Trials DataFrame':
            df = analyser.export_trials_dataframe()
            filename = questionary.text('Enter filename to save as (e.g. trials.csv):').ask()
            if filename:
                df.to_csv(filename, index=False)
                print(f'Exported to {filename}')
        elif action == '🧮 Plot Hyperparameter Correlation Matrix':
            analyser.plot_hyperparameter_correlation_matrix()
        elif action == '📊 Plot Parameter Stability':
            analyser.plot_parameter_stability()
        elif action == '📺 Launch Optuna HTML Dashboard':
            analyser.launch_dashboard()
        elif action == '❌ Quit':
            break


if __name__ == '__main__':
    analyse_study()
