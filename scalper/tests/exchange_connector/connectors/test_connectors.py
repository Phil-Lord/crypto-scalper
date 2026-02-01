import pytest
from unittest.mock import Mock

from exchange_connector.connectors.trades_connector import TradesConnector
from exchange_connector.api.kraken_api_client import KrakenApiClient
from data_system.models.trade_model import Trade


@pytest.mark.exchange_connector
@pytest.mark.connectors
@pytest.mark.trades_connector
class TestTradesConnector:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    @pytest.fixture
    def raw_trade_data(self):
        return [
            ['50000.0', '0.001', 1704067200.123, 'b', 'm', '', 123456789],
            ['50001.0', '0.002', 1704067201.456, 's', 'l', '', 123456790],
        ]

    def test_init_with_injected_client(self, mock_client):
        # When
        connector = TradesConnector(client=mock_client)

        # Then
        assert connector.client == mock_client

    def test_init_creates_default_client_when_none_provided(self):
        # When
        connector = TradesConnector()

        # Then
        assert connector.client is not None
        assert isinstance(connector.client, KrakenApiClient)

    def test_fetch_returns_trade_objects(self, mock_client, raw_trade_data):
        # Given
        connector = TradesConnector(client=mock_client)
        connector.service = Mock()
        connector.service.fetch_trades.return_value = raw_trade_data

        # When
        trades = connector.fetch('XXBTZGBP', 1704067200000000000, 1704153600000000000)

        # Then
        assert len(trades) == 2
        assert all(isinstance(t, Trade) for t in trades)

    def test_to_domain_converts_raw_data_to_trade_objects(self, mock_client, raw_trade_data):
        # Given
        connector = TradesConnector(client=mock_client)

        # When
        trades = connector._to_domain(raw_trade_data, 'XXBTZGBP')

        # Then
        assert len(trades) == 2

        # Check first trade
        assert trades[0].trade_id == 123456789
        assert trades[0].pair == 'XXBTZGBP'
        assert trades[0].price == 50000.0
        assert trades[0].volume == 0.001
        assert trades[0].timestamp == 1704067200.123
        assert trades[0].side == 'b'
        assert trades[0].order_type == 'm'

        # Check second trade
        assert trades[1].trade_id == 123456790
        assert trades[1].side == 's'
        assert trades[1].order_type == 'l'


@pytest.mark.exchange_connector
@pytest.mark.connectors
@pytest.mark.add_order_connector
class TestAddOrderConnector:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    def test_init_with_injected_client(self, mock_client):
        # Given
        from exchange_connector.connectors.add_order_connector import AddOrderConnector

        # When
        connector = AddOrderConnector(client=mock_client)

        # Then
        assert connector.client == mock_client

    def test_place_calls_service_add_order(self, mock_client):
        # Given
        from exchange_connector.connectors.add_order_connector import AddOrderConnector
        connector = AddOrderConnector(client=mock_client)
        connector.service = Mock()
        connector.service.add_order.return_value = {'txid': ['ORDER-123']}

        # When
        result = connector.place('XXBTZGBP', 'buy', 100.0)

        # Then
        connector.service.add_order.assert_called_once_with('XXBTZGBP', 'buy', 100.0)
        assert result == {'txid': ['ORDER-123']}


@pytest.mark.exchange_connector
@pytest.mark.connectors
@pytest.mark.balance_connector
class TestBalanceConnector:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    def test_init_with_injected_client(self, mock_client):
        # Given
        from exchange_connector.connectors.balance_connector import BalanceConnector

        # When
        connector = BalanceConnector(client=mock_client)

        # Then
        assert connector.client == mock_client

    def test_fetch_calls_service_fetch_balances(self, mock_client):
        # Given
        from exchange_connector.connectors.balance_connector import BalanceConnector
        connector = BalanceConnector(client=mock_client)
        connector.service = Mock()
        connector.service.fetch_balances.return_value = {'XXBT': '1.5', 'ZGBP': '1000.0'}

        # When
        result = connector.fetch()

        # Then
        connector.service.fetch_balances.assert_called_once()
        assert result == {'XXBT': '1.5', 'ZGBP': '1000.0'}


@pytest.mark.exchange_connector
@pytest.mark.connectors
@pytest.mark.ticker_connector
class TestTickerConnector:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    def test_init_with_injected_client(self, mock_client):
        # Given
        from exchange_connector.connectors.ticker_connector import TickerConnector

        # When
        connector = TickerConnector(client=mock_client)

        # Then
        assert connector.client == mock_client

    def test_fetch_calls_service_fetch_ticker(self, mock_client):
        # Given
        from exchange_connector.connectors.ticker_connector import TickerConnector
        connector = TickerConnector(client=mock_client)
        connector.service = Mock()
        connector.service.fetch_ticker.return_value = {'a': ['50000.0'], 'b': ['49999.0']}

        # When
        result = connector.fetch('XXBTZGBP')

        # Then
        connector.service.fetch_ticker.assert_called_once_with('XXBTZGBP')
        assert result == {'a': ['50000.0'], 'b': ['49999.0']}


@pytest.mark.exchange_connector
@pytest.mark.connectors
@pytest.mark.asset_pairs_connector
class TestAssetPairsConnector:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    def test_init_with_injected_client(self, mock_client):
        # Given
        from exchange_connector.connectors.asset_pairs_connector import AssetPairsConnector

        # When
        connector = AssetPairsConnector(client=mock_client)

        # Then
        assert connector.client == mock_client


@pytest.mark.exchange_connector
@pytest.mark.connectors
@pytest.mark.ohlc_connector
class TestOhlcConnector:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    def test_init_with_injected_client(self, mock_client):
        # Given
        from exchange_connector.connectors.ohlc_connector import OhlcConnector

        # When
        connector = OhlcConnector(client=mock_client)

        # Then
        assert connector.client == mock_client

    def test_fetch_calls_service_fetch_ohlc(self, mock_client):
        # Given
        from exchange_connector.connectors.ohlc_connector import OhlcConnector
        connector = OhlcConnector(client=mock_client)
        connector.service = Mock()
        ohlc_data = [[1704067200, '50000', '50100', '49900', '50050', '100', '5000000', 10]]
        connector.service.fetch_ohlc.return_value = ohlc_data

        # When
        result = connector.fetch('XXBTZGBP', 1, 1704067200)

        # Then
        connector.service.fetch_ohlc.assert_called_once_with('XXBTZGBP', 1, 1704067200)
        assert result == ohlc_data
