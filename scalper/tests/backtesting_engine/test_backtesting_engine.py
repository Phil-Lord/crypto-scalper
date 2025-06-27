import pandas as pd

from backtesting_engine.backtesting_engine import BacktestingEngine


class DummyStrategy:
    def __init__(self):
        self.called = False

    def vectorised_compute(self, ohlc):
        self.called = True
        return pd.DataFrame({'signal': ['hold']*len(ohlc)}, index=ohlc.index)

    def generate_signal(self, row):
        return {'signal': 'hold'}


def test_run_vectorised(monkeypatch):
    dummy_strategy = DummyStrategy()
    monkeypatch.setattr('strategy_manager.StrategyManager.get_strategy',
                        lambda self, name, **kwargs: dummy_strategy)
    engine = BacktestingEngine('BTCGBP', 'dummy')
    dummy_ohlc = pd.DataFrame({'price': [100, 101, 102]}, index=[1, 2, 3])
    monkeypatch.setattr(engine, '_BacktestingEngine__load_resampled_ohlc',
                        lambda: setattr(engine, 'resampled_ohlc', dummy_ohlc))
    engine.strategy = dummy_strategy
    engine.vectorised = True
    results = engine.run()
    assert engine.strategy.called
    assert (results['signal'] == 'hold').all()


def test_run_non_vectorised(monkeypatch):
    dummy_strategy = DummyStrategy()
    monkeypatch.setattr('strategy_manager.StrategyManager.get_strategy',
                        lambda self, name, **kwargs: dummy_strategy)
    engine = BacktestingEngine('BTCGBP', 'dummy')
    dummy_ohlc = pd.DataFrame({'price': [100, 101]}, index=[1, 2])
    monkeypatch.setattr(engine, '_BacktestingEngine__load_resampled_ohlc',
                        lambda: setattr(engine, 'resampled_ohlc', dummy_ohlc))
    engine.strategy = dummy_strategy
    engine.vectorised = False
    results = engine.run()
    assert (results['signal'] == 'hold').all()
