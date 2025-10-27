import pytest

from trade_executor.trade_executor import TradeExecutor


@pytest.mark.trade_executor
class TestTradeExecutor:
    MODULE_NAME = 'trade_executor.trade_executor'

    @pytest.fixture()
    def strategy_manager_patch(self, mocker):
        mock_strategy = mocker.MagicMock()
        manager_patch = mocker.patch(f'{self.MODULE_NAME}.StrategyManager')
        manager_patch.return_value.get_strategy.return_value = mock_strategy
        manager_patch.mock_strategy = mock_strategy
        return manager_patch

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
    def test_trade_executor(self, strategy_manager_patch, add_order_connector_patch,
                            balance_connector_patch, ticker_connector_patch):
        # Given
        ticker_connector_patch.fetch.return_value = {'c': [50]}
        strategy_manager_patch.mock_strategy.generate_signal.return_value = {'signal': 'buy'}
        balance_connector_patch.fetch.return_value = {'ZGBP': 100, 'XXBT': 0}
        add_order_connector_patch.place.return_value = {
            'txid': 'testId',
            'descr': {'order': 'buy 0.002 BTC at 50 GBP'}
        }

        # When
        executor = TradeExecutor('XXBTZGBP', 1, 'testStrategy', param1=10, param2=20)
        executor.execute_interval()

        # Then
        strategy_manager_patch().get_strategy.assert_called_once_with(
            'testStrategy', param1=10, param2=20
        )
        ticker_connector_patch.fetch.assert_called_once_with('XXBTZGBP')
        strategy_manager_patch.mock_strategy.generate_signal.assert_called_once_with(50)
        balance_connector_patch.fetch.assert_called_once()
        add_order_connector_patch.place.assert_called_once_with('XXBTZGBP', 'buy', 100)
