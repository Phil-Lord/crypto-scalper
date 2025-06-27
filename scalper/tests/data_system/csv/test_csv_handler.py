import pytest

from data_system.csv import CsvHandler
from data_system.csv.exceptions import MissingTradesFileException


def test_save_and_load_trades(tmp_path):
    pair = 'BTCGBP'
    handler = CsvHandler(pair)
    handler.storage_path = tmp_path / f'{pair}-trades.csv'
    raw_trades = [[100, 1, 1234567890, 'b', 'l', 'misc', 1]]
    handler.save_trades(raw_trades)
    loaded = handler.load_trades()
    assert not loaded.empty
    assert 'price' in loaded.columns
    assert loaded.index.name == 'trade_id'


def test_load_trades_missing(tmp_path):
    pair = 'ETHGBP'
    handler = CsvHandler(pair)
    handler.storage_path = tmp_path / f'{pair}-trades.csv'
    with pytest.raises(MissingTradesFileException):
        handler.load_trades()
    # Should not raise if create_if_missing=True
    df = handler.load_trades(create_if_missing=True)
    assert df.empty
