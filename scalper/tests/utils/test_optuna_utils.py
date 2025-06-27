from utils import get_study_names


def test_get_study_names(monkeypatch):
    class DummySummary:
        def __init__(self, name):
            self.study_name = name

    class DummyRDBStorage:
        def __init__(self, url):
            pass

    class DummyOptuna:
        class storages:
            RDBStorage = DummyRDBStorage

        class study:
            @staticmethod
            def get_all_study_summaries(storage=None):
                return [DummySummary('a'), DummySummary('b')]

    monkeypatch.setattr('utils.optuna_utils.optuna', DummyOptuna)
    monkeypatch.setattr('utils.optuna_utils.OPTUNA_DB_URL', 'dummy')
    names = get_study_names()
    assert names == ['a', 'b']
