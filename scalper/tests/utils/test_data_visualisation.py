import pandas as pd
import pytest

from utils import plot_position_profits, plot_results, plot_trade_data_from_db


@pytest.mark.utils
@pytest.mark.data_visualisation
class TestPlotPositionProfits:
    def test_plots_profit_bars(self, monkeypatch):
        # Given
        monkeypatch.setattr('matplotlib.pyplot.show', lambda: None)
        df = pd.DataFrame({'profit': [1, -1]}, index=[0, 1])

        # When / Then (no exception)
        plot_position_profits(df)

    def test_handles_empty_dataframe(self, monkeypatch, capsys):
        # Given
        monkeypatch.setattr('matplotlib.pyplot.show', lambda: None)

        # When
        plot_position_profits(pd.DataFrame())

        # Then
        captured = capsys.readouterr()
        assert 'No positions to plot' in captured.out


@pytest.mark.utils
@pytest.mark.data_visualisation
class TestPlotResults:
    def test_plots_price_with_signals(self, monkeypatch):
        # Given
        monkeypatch.setattr('matplotlib.pyplot.show', lambda: None)
        df = pd.DataFrame(
            {'price': [1, 2, 3], 'signal': ['buy', 'sell', 'hold']},
            index=[0, 1, 2],
        )

        # When / Then (no exception)
        plot_results(df, 'BTCGBP')


@pytest.mark.utils
@pytest.mark.data_visualisation
class TestPlotTradeDataFromDb:
    def test_plots_trade_prices(self, monkeypatch):
        # Given
        monkeypatch.setattr('matplotlib.pyplot.show', lambda: None)

        class MockTrade:
            def __init__(self, timestamp, price, volume, side):
                self.timestamp = timestamp
                self.price = price
                self.volume = volume
                self.side = side

        trades = [MockTrade(1, 100, 0.1, 'b'), MockTrade(2, 101, 0.2, 's')]

        # When / Then (no exception)
        plot_trade_data_from_db(trades)

    def test_handles_empty_list(self, monkeypatch, capsys):
        # Given
        monkeypatch.setattr('matplotlib.pyplot.show', lambda: None)

        # When
        plot_trade_data_from_db([])

        # Then
        captured = capsys.readouterr()
        assert 'No trades to plot' in captured.out
