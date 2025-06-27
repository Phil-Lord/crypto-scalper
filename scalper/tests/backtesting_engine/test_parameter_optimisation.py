from backtesting_engine.parameter_optimisation import get_objective, TqdmProgressCallback


def test_get_objective_returns_callable():
    class DummyEngine:
        def __init__(self):
            self.strategy = type('S', (), {})()

        def run(self):
            return None

        def get_final_quote_balance(self):
            return 42

    param_grid = {'a': [1, 2]}
    obj = get_objective(DummyEngine(), param_grid)
    assert callable(obj)


def test_tqdm_progress_callback():
    cb = TqdmProgressCallback(2)

    class DummyTrial:
        pass

    class DummyStudy:
        pass

    cb(DummyStudy(), DummyTrial())
    cb.close()
