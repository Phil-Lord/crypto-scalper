import optuna
import matplotlib.pyplot as plt
import seaborn as sns


class StudyPlotter:
    @staticmethod
    def plot_hyperparameter_correlation_matrix(study: optuna.study.Study) -> None:
        df = study.trials_dataframe(attrs=('number', 'value', 'params'))
        param_cols = [col for col in df.columns if col.startswith('params_')]
        corr = df[param_cols].corr()
        sns.heatmap(corr, annot=True, cmap='coolwarm')
        plt.title('Hyperparameter Correlation Matrix')
        plt.tight_layout()
        plt.show()

    @staticmethod
    def plot_parameter_stability(study: optuna.study.Study) -> None:
        top_n = 100
        df = study.trials_dataframe(attrs=('number', 'value', 'params'))
        df_top = df.sort_values('value', ascending=False).head(top_n)
        param_cols = [col for col in df_top.columns if col.startswith('params_')]
        df_params = df_top[['number'] + param_cols]

        df_norm = df_params.copy()
        for col in param_cols:
            min_val = df_norm[col].min()
            max_val = df_norm[col].max()
            range_val = max_val - min_val
            if range_val == 0:
                df_norm[col] = 0.5  # constant value across trials
            else:
                df_norm[col] = (df_norm[col] - min_val) / range_val

        melted = df_norm.melt(id_vars='number', var_name='param', value_name='value')

        plt.figure(figsize=(10, 6))
        sns.boxplot(data=melted, x='param', y='value')
        sns.stripplot(data=melted, x='param', y='value',
                      color='black', size=3, jitter=0.2, alpha=0.6)
        title = f'Normalised Parameter Stability (Top {top_n} Trials)'
        plt.ylabel('Normalised Value (0-1)')
        plt.title(title)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
