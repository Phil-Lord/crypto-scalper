from study_analyser import StudyAnalyser


class DummyStudy:
    study_name = 'dummy'
    trials = [1, 2, 3]
    best_value = 42
    best_params = {'a': 1}

    def trials_dataframe(self, attrs=None):
        return 'df'


class DummyRDBStorage:
    def __init__(self, url, engine_kwargs=None):
        pass


class DummyOptuna:
    class storages:
        RDBStorage = DummyRDBStorage

    @staticmethod
    def load_study(study_name, storage):
        return DummyStudy()


def test_study_analyser_load(monkeypatch):
    monkeypatch.setattr('study_analyser.study_analyser.optuna', DummyOptuna)
    monkeypatch.setattr('study_analyser.study_analyser.OPTUNA_DB_URL', 'dummy')
    analyser = StudyAnalyser('dummy')
    assert analyser.study.study_name == 'dummy'
    assert analyser.describe() is None
    assert analyser.export_trials_dataframe() == 'df'
