import pytest
from unittest.mock import Mock

from exchange_connector.api.kraken_api_client import KrakenApiClient
from exchange_connector.connectors.add_order_connector import AddOrderConnector
from exchange_connector.connectors.asset_pairs_connector import AssetPairsConnector
from exchange_connector.connectors.balance_connector import BalanceConnector
from exchange_connector.connectors.ohlc_connector import OhlcConnector
from exchange_connector.connectors.ticker_connector import TickerConnector
from exchange_connector.connectors.trades_connector import TradesConnector
from exchange_connector.models import OrderResult
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

    @pytest.fixture
    def raw_order_response(self):
        return {
            'txid': ['ORDER-123'],
            'descr': {'order': 'buy 100.00000000 XXBTZGBP @ market'}
        }

    def test_init_with_injected_client(self, mock_client):
        # When
        connector = AddOrderConnector(client=mock_client)

        # Then
        assert connector.client == mock_client

    def test_place_returns_order_result(self, mock_client, raw_order_response):
        # Given
        connector = AddOrderConnector(client=mock_client)
        connector.service = Mock()
        connector.service.add_order.return_value = raw_order_response

        # When
        result = connector.place('XXBTZGBP', 'buy', 100.0)

        # Then
        connector.service.add_order.assert_called_once_with('XXBTZGBP', 'buy', 100.0)
        assert isinstance(result, OrderResult)
        assert result.txid == ['ORDER-123']
        assert result.order_description == 'buy 100.00000000 XXBTZGBP @ market'

    def test_to_domain_converts_raw_response(self, mock_client, raw_order_response):
        # Given
        connector = AddOrderConnector(client=mock_client)

        # When
        result = connector._to_domain(raw_order_response)

        # Then
        assert result.txid == ['ORDER-123']
        assert result.order_description == 'buy 100.00000000 XXBTZGBP @ market'

    def test_to_domain_raises_on_missing_txid(self, mock_client):
        # Given
        connector = AddOrderConnector(client=mock_client)
        invalid_response = {'descr': {'order': 'test'}}

        # When / Then
        with pytest.raises(ValueError, match='Missing transaction ID'):
            connector._to_domain(invalid_response)

    def test_to_domain_handles_missing_description(self, mock_client):
        # Given
        connector = AddOrderConnector(client=mock_client)
        response_without_descr = {'txid': ['ORDER-123']}

        # When
        result = connector._to_domain(response_without_descr)

        # Then
        assert result.txid == ['ORDER-123']
        assert result.order_description == ''


@pytest.mark.exchange_connector
@pytest.mark.connectors
@pytest.mark.balance_connector
class TestBalanceConnector:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    def test_init_with_injected_client(self, mock_client):
        # When
        connector = BalanceConnector(client=mock_client)

        # Then
        assert connector.client == mock_client

    def test_fetch_calls_service_fetch_balances(self, mock_client):
        # Given
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
        # When
        connector = TickerConnector(client=mock_client)

        # Then
        assert connector.client == mock_client

    def test_fetch_calls_service_fetch_ticker(self, mock_client):
        # Given
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
        # When
        connector = OhlcConnector(client=mock_client)

        # Then
        assert connector.client == mock_client

    def test_fetch_calls_service_fetch_ohlc(self, mock_client):
        # Given
        connector = OhlcConnector(client=mock_client)
        connector.service = Mock()
        ohlc_data = [[1704067200, '50000', '50100', '49900', '50050', '100', '5000000', 10]]
        connector.service.fetch_ohlc.return_value = ohlc_data

        # When
        result = connector.fetch('XXBTZGBP', 1, 1704067200)

        # Then
        connector.service.fetch_ohlc.assert_called_once_with('XXBTZGBP', 1, 1704067200)
        assert result == ohlc_data
