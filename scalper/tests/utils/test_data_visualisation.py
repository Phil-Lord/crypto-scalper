import pandas as pd

from utils import plot_position_profits, plot_results, plot_trade_data_from_db


def test_plot_position_profits(monkeypatch):
    monkeypatch.setattr('matplotlib.pyplot.show', lambda: None)
    df = pd.DataFrame({'profit': [1, -1]}, index=[0, 1])
    plot_position_profits(df)
    plot_position_profits(pd.DataFrame())


def test_plot_results(monkeypatch):
    monkeypatch.setattr('matplotlib.pyplot.show', lambda: None)
    df = pd.DataFrame({'price': [1, 2, 3], 'signal': ['buy', 'sell', 'hold']}, index=[0, 1, 2])
    plot_results(df, 'BTCGBP')


def test_plot_trade_data_from_db(monkeypatch):
    monkeypatch.setattr('matplotlib.pyplot.show', lambda: None)
    df = pd.DataFrame({'timestamp': [1, 2], 'price': [100, 101]})
    plot_trade_data_from_db(df)
