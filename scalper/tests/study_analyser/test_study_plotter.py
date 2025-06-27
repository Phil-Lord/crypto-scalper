from study_analyser.study_plotter import StudyPlotter


class DummyStudy:
    def trials_dataframe(self, attrs=None):
        import pandas as pd
        return pd.DataFrame({
            'number': [1, 2],
            'value': [0.5, 0.7],
            'params_a': [1, 2],
            'params_b': [3, 4]
        })


def test_plot_hyperparameter_correlation_matrix(monkeypatch):
    monkeypatch.setattr('matplotlib.pyplot.show', lambda: None)
    monkeypatch.setattr('seaborn.heatmap', lambda *a, **k: None)
    StudyPlotter.plot_hyperparameter_correlation_matrix(DummyStudy())


def test_plot_parameter_stability(monkeypatch):
    monkeypatch.setattr('matplotlib.pyplot.show', lambda: None)
    monkeypatch.setattr('seaborn.boxplot', lambda *a, **k: None)
    monkeypatch.setattr('seaborn.stripplot', lambda *a, **k: None)
    StudyPlotter.plot_parameter_stability(DummyStudy())
