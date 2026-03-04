import logging
import pytest

from exchange_connector.models import AddOrderResult
from trade_executor.trade_executor import TradeExecutor


@pytest.mark.trade_executor
class TestTradeExecutor:
    MODULE_NAME = 'trade_executor.trade_executor'

    @pytest.fixture()
    def mock_strategy(self, mocker):
        ''' Mock strategy that can be passed to TradeExecutor. '''
        mock = mocker.MagicMock()
        mock.__class__.__name__ = 'TestStrategy'
        return mock

    @pytest.fixture()
    def add_order_connector_patch(self, mocker):
        return mocker.patch(f'{self.MODULE_NAME}.AddOrderConnector').return_value

    @pytest.fixture()
    def balance_connector_patch(self, mocker):
        return mocker.patch(f'{self.MODULE_NAME}.BalanceConnector').return_value

    @pytest.fixture()
    def ticker_connector_patch(self, mocker):
        return mocker.patch(f'{self.MODULE_NAME}.TickerConnector').return_value

    @pytest.mark.execute_interval
    def test_execute_interval_buy(
        self, caplog, mock_strategy, add_order_connector_patch,
        balance_connector_patch, ticker_connector_patch
    ):
        # Given
        ticker_connector_patch.fetch.return_value = {'c': [50]}
        mock_strategy.generate_signal.return_value = {'signal': 'buy'}
        balance_connector_patch.fetch.return_value = {'ZGBP': 100, 'XXBT': 0}
        add_order_connector_patch.place.return_value = AddOrderResult(
            txid=['testId'],
            order_description='buy 0.002 BTC at 50 GBP'
        )

        # When
        caplog.set_level(logging.INFO)
        executor = TradeExecutor('XXBTZGBP', 1, mock_strategy)
        executor.execute_interval()

        # Then
        self.assert_logged_messages(caplog, [
            "Initialised TradeExecutor: XXBTZGBP - TestStrategy",
            "Interval result: price=50.00, signal=buy",
            "Placing BUY order: volume=100",
            "Trade executed: id=testId, order=buy 0.002 BTC at 50 GBP"
        ])

        ticker_connector_patch.fetch.assert_called_once_with('XXBTZGBP')
        mock_strategy.generate_signal.assert_called_once_with(50)
        balance_connector_patch.fetch.assert_called_once()
        add_order_connector_patch.place.assert_called_once_with('XXBTZGBP', 'buy', 100)

    @pytest.mark.execute_interval
    def test_execute_interval_sell(
        self, caplog, mock_strategy, add_order_connector_patch,
        balance_connector_patch, ticker_connector_patch
    ):
        # Given
        ticker_connector_patch.fetch.return_value = {'c': [50]}
        mock_strategy.generate_signal.return_value = {'signal': 'sell'}
        balance_connector_patch.fetch.return_value = {'ZGBP': 0, 'XXBT': 1}
        add_order_connector_patch.place.return_value = AddOrderResult(
            txid=['testId'],
            order_description='sell 1 BTC at 50 GBP'
        )

        # When
        caplog.set_level(logging.INFO)
        executor = TradeExecutor('XXBTZGBP', 1, mock_strategy)
        executor.execute_interval()

        # Then
        self.assert_logged_messages(caplog, [
            "Initialised TradeExecutor: XXBTZGBP - TestStrategy",
            "Interval result: price=50.00, signal=sell",
            "Placing SELL order: volume=1",
            "Trade executed: id=testId, order=sell 1 BTC at 50 GBP"
        ])

        ticker_connector_patch.fetch.assert_called_once_with('XXBTZGBP')
        mock_strategy.generate_signal.assert_called_once_with(50)
        balance_connector_patch.fetch.assert_called_once()
        add_order_connector_patch.place.assert_called_once_with('XXBTZGBP', 'sell', 1)

    @pytest.mark.execute_interval
    def test_execute_interval_hold(
        self, caplog, mock_strategy, add_order_connector_patch,
        balance_connector_patch, ticker_connector_patch
    ):
        # Given
        ticker_connector_patch.fetch.return_value = {'c': [50]}
        mock_strategy.generate_signal.return_value = {'signal': 'hold'}

        # When
        caplog.set_level(logging.INFO)
        executor = TradeExecutor('XXBTZGBP', 1, mock_strategy)
        executor.execute_interval()

        # Then
        self.assert_logged_messages(caplog, [
            "Initialised TradeExecutor: XXBTZGBP - TestStrategy",
            "Interval result: price=50.00, signal=hold"
        ])

        ticker_connector_patch.fetch.assert_called_once_with('XXBTZGBP')
        mock_strategy.generate_signal.assert_called_once_with(50)
        balance_connector_patch.fetch.assert_not_called()
        add_order_connector_patch.place.assert_not_called()

    def assert_logged_messages(self, caplog, expected_messages):
        assert len(caplog.records) == len(expected_messages)
        for i, message in enumerate(expected_messages):
            assert caplog.records[i].message == message
