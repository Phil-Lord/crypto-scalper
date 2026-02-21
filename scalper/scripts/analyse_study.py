import logging
import subprocess

import click
import questionary

from study_analyser import StudyAnalyser
from utils import load_env, LOG_FORMAT, get_study_choices, OptunaConfig

load_env()
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


@click.command()
@click.option('--dashboard', '-d', is_flag=True, help='Launch Optuna HTML Dashboard.')
def analyse_study(dashboard: bool = False) -> None:
    if dashboard:
        launch_optuna_dashboard()

    study_choices = get_study_choices()
    if not study_choices:
        print('No studies found.')
        return

    study_name = questionary.select('Select a study:', choices=study_choices).ask()
    analyser = StudyAnalyser(study_name)
    run_analysis_dashboard(analyser)


def launch_optuna_dashboard() -> None:
    url = OptunaConfig.DB_URL.replace('postgresql://', 'postgresql+psycopg2://')
    print('Launching Optuna dashboard at http://localhost:8080 ...')
    subprocess.run(['optuna-dashboard', url])


def run_analysis_dashboard(analyser: StudyAnalyser) -> None:
    while True:
        action = questionary.select(
            'Select an action:',
            choices=[
                '📄 Describe Study',
                '🔢 Describe Trial by Number',
                '📤 Export Trials DataFrame',
                '🧮 Plot Hyperparameter Correlation Matrix',
                '📊 Plot Parameter Stability',
                '❌ Quit'
            ]
        ).ask()

        if action == '📄 Describe Study':
            analyser.describe()
        elif action == '🔢 Describe Trial by Number':
            trial_number = questionary.text('Enter trial number:').ask()
            analyser.describe_trial_by_number(int(trial_number))
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
        elif action == '❌ Quit':
            break


if __name__ == '__main__':
    analyse_study()
