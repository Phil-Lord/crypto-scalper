import optuna
import matplotlib.pyplot as plt
import seaborn as sns


class StudyPlotter:
    @staticmethod
    def plot_optimisation_history(study: optuna.study.Study) -> None:
        optuna.visualization.matplotlib.plot_optimization_history(study)
        plt.title('Optimisation History')
        plt.tight_layout()
        plt.show()

    @staticmethod
    def plot_param_importances(study: optuna.study.Study) -> None:
        optuna.visualization.matplotlib.plot_param_importances(study)
        plt.title('Hyperparameter Importances')
        plt.tight_layout()
        plt.show()

    @staticmethod
    def plot_params_vs_objective(study: optuna.study.Study) -> None:
        df = study.trials_dataframe(attrs=('number', 'value', 'params'))
        best_params = study.best_params

        for param in best_params:
            if param not in df.columns:
                continue

            plt.figure(figsize=(8, 5))
            sns.scatterplot(data=df, x=param, y='value')
            plt.title(f'{param} vs Objective Value')
            plt.xlabel(param)
            plt.ylabel('Final Quote Balance')
            plt.tight_layout()
            plt.show()
