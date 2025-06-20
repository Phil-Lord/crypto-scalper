import subprocess

import questionary

from study_analyser import StudyAnalyser
from utils import get_study_names, OPTUNA_DB_URL


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
                '📈 Plot Optimisation History',
                '🧮 Plot Parameter Importances',
                '📊 Plot Params vs Objective',
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

        elif action == '📈 Plot Optimisation History':
            analyser.plot_optimisation_history()

        elif action == '🧮 Plot Parameter Importances':
            analyser.plot_param_importances()

        elif action == '📊 Plot Params vs Objective':
            analyser.plot_params_vs_objective()

        elif action == '📺 Launch Optuna HTML Dashboard':
            url = OPTUNA_DB_URL.replace('postgresql://', 'postgresql+psycopg2://')
            print('Launching Optuna dashboard at http://localhost:8080 ...')
            subprocess.run(['optuna-dashboard', url])

        elif action == '❌ Quit':
            break


if __name__ == '__main__':
    analyse_study()
