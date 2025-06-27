import pandas as pd

from data_system.repositories import TradesRepository


class DummySession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class DummyCRUD:
    def __init__(self, session):
        self.session = session
        self.added = False

    def add_trades(self, trades, pair):
        self.added = True

    def get_trades(self, pair, start, end):
        return pd.DataFrame({'price': [100], 'volume': [1]})


def test_add_and_get(monkeypatch):
    repo = TradesRepository()
    monkeypatch.setattr('data_system.repositories.trades_repository.SessionLocal',
                        lambda: DummySession())
    monkeypatch.setattr('data_system.repositories.trades_repository.TradeCRUD', DummyCRUD)
    repo.add([[100, 1, 1234567890, 'b', 'l', 'misc', 1]], 'BTCGBP')
    df = repo.get('BTCGBP')
    assert not df.empty
    assert 'price' in df.columns
