import pytest

from trade_executor.trade_executor import TradeExecutor


@pytest.mark.trade_executor
class TestTradeExecutor:
    @pytest.fixture()
    def strategy_manager_patch(self, mocker):
        patch = mocker.patch('trade_executor.trade_executor.StrategyManager')
        patch.return_value.get_strategy.return_value = None
        return patch

    @pytest.fixture()
    def add_order_connector_patch(self, mocker):
        return mocker.patch('trade_executor.trade_executor.AddOrderConnector')

    @pytest.fixture()
    def balance_connector_patch(self, mocker):
        return mocker.patch('trade_executor.trade_executor.BalanceConnector')

    @pytest.fixture()
    def ticker_connector_patch(self, mocker):
        return mocker.patch('trade_executor.trade_executor.TickerConnector')

    @pytest.mark.execute_interval
    def test_trade_executor(self, strategy_manager_patch, add_order_connector_patch,
                            balance_connector_patch, ticker_connector_patch):
        # Given
        ticker_connector_patch.fetch.return_value = {'c': [50]}
        strategy_manager_patch.generate_signal.return_value = {'signal': 'buy'}
        balance_connector_patch.fetch.return_value = {'GBP': 100, 'BTC': 0}
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
        strategy_manager_patch().generate_signal.assert_called_once_with(50.0)
        balance_connector_patch.fetch.assert_called_once()
        add_order_connector_patch.place.assert_called_once_with('XXBTZGBP', 'buy', 100)
