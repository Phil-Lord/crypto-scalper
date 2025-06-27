import pytest


class DummyFileHandler:
    def __init__(self, *a, **k): pass
    def setFormatter(self, *a, **k): pass
    def setLevel(self, *a, **k): pass
    def emit(self, *a, **k): pass
    def close(self): pass


class DummyTicker:
    def fetch(self, pair):
        return {'c': [100]}


class DummyBalance:
    def fetch(self):
        return {'ZGBP': 1000, 'XXBT': 1}


class DummyOrder:
    def place(self, pair, signal, volume):
        return {'txid': '1', 'descr': {'order': 'buy'}}


class DummyStrategy:
    def generate_signal(self, price):
        return {'signal': 'buy'}

    def __class__(self):
        return type('S', (), {})


@pytest.fixture(autouse=True)
def patch_filehandler(monkeypatch):
    monkeypatch.setattr('logging.FileHandler', DummyFileHandler)


def test_trade_executor(monkeypatch):
    from trade_executor.trade_executor import TradeExecutor

    monkeypatch.setattr('logging.FileHandler', DummyFileHandler)
    monkeypatch.setattr('strategy_manager.StrategyManager.get_strategy',
                        lambda self, name, **kwargs: DummyStrategy())
    executor = TradeExecutor('XXBTZGBP', 1, 'dummy')
    executor.ticker_connector = DummyTicker()
    executor.balance_connector = DummyBalance()
    executor.add_order_connector = DummyOrder()
    executor.strategy = DummyStrategy()
    assert executor.get_price() == 100
    assert executor.run_strategy(100) == 'buy'
    executor.log_interval_results(100, 'buy')
    executor.execute_trade('buy')
    executor.execute_trade('sell')
