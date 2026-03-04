import pytest
from unittest.mock import Mock

from exchange_connector.api.kraken_api_client import KrakenApiClient
from exchange_connector.api.exceptions import KrakenApiResponseError
from exchange_connector.connectors.add_order_connector import AddOrderConnector
from exchange_connector.connectors.asset_pairs_connector import AssetPairsConnector
from exchange_connector.connectors.balance_connector import BalanceConnector
from exchange_connector.connectors.ohlc_connector import OhlcConnector
from exchange_connector.connectors.ticker_connector import TickerConnector
from exchange_connector.connectors.trades_connector import TradesConnector
from exchange_connector.models import AddOrderResult
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

    def test_to_domain_raises_on_incomplete_trade_data(self, mock_client):
        # Given
        connector = TradesConnector(client=mock_client)
        incomplete_trade = [['50000.0', '0.001', 1704067200.123]]  # Only 3 fields instead of 7

        # When / Then
        with pytest.raises(ValueError, match='Trade data incomplete'):
            connector._to_domain(incomplete_trade, 'XXBTZGBP')

    def test_to_domain_raises_on_invalid_price(self, mock_client):
        # Given
        connector = TradesConnector(client=mock_client)
        invalid_trade = [['invalid_price', '0.001', 1704067200.123, 'b', 'm', '', 123456789]]

        # When / Then
        with pytest.raises(ValueError, match='Failed to parse trade data'):
            connector._to_domain(invalid_trade, 'XXBTZGBP')

    def test_to_domain_raises_on_invalid_volume(self, mock_client):
        # Given
        connector = TradesConnector(client=mock_client)
        invalid_trade = [['50000.0', 'bad_volume', 1704067200.123, 'b', 'm', '', 123456789]]

        # When / Then
        with pytest.raises(ValueError, match='Failed to parse trade data'):
            connector._to_domain(invalid_trade, 'XXBTZGBP')

    def test_to_domain_raises_on_invalid_trade_id(self, mock_client):
        # Given
        connector = TradesConnector(client=mock_client)
        invalid_trade = [['50000.0', '0.001', 1704067200.123, 'b', 'm', '', 'not_a_number']]

        # When / Then
        with pytest.raises(ValueError, match='Failed to parse trade data'):
            connector._to_domain(invalid_trade, 'XXBTZGBP')

    def test_to_domain_handles_empty_list(self, mock_client):
        # Given
        connector = TradesConnector(client=mock_client)

        # When
        trades = connector._to_domain([], 'XXBTZGBP')

        # Then
        assert trades == []

    def test_fetch_passes_parameters_to_service(self, mock_client):
        # Given
        connector = TradesConnector(client=mock_client)
        connector.service = Mock()
        connector.service.fetch_trades.return_value = []
        start = 1704067200000000000
        end = 1704153600000000000

        # When
        connector.fetch('XXBTZGBP', start, end)

        # Then
        connector.service.fetch_trades.assert_called_once_with('XXBTZGBP', start, end)


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
        connector.service.add_order.assert_called_once_with('XXBTZGBP', 'buy', 100.0, False)
        assert isinstance(result, AddOrderResult)
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

    def test_to_domain_handles_missing_description(self, mock_client):
        # Given
        connector = AddOrderConnector(client=mock_client)
        response_without_descr = {'txid': ['ORDER-123']}

        # When / Then
        with pytest.raises(ValueError, match='Missing order description'):
            connector._to_domain(response_without_descr)

    def test_to_domain_handles_nested_description(self, mock_client):
        # Given
        connector = AddOrderConnector(client=mock_client)
        response = {
            'txid': ['ORDER-456'],
            'descr': {'order': 'sell 0.50000000 XXBTZGBP @ market'}
        }

        # When
        result = connector._to_domain(response)

        # Then
        assert result.txid == ['ORDER-456']
        assert result.order_description == 'sell 0.50000000 XXBTZGBP @ market'

    def test_to_domain_handles_multiple_txids(self, mock_client):
        # Given
        connector = AddOrderConnector(client=mock_client)
        response = {
            'txid': ['ORDER-001', 'ORDER-002'],
            'descr': {'order': 'buy 100.00000000 XXBTZGBP @ market'}
        }

        # When
        result = connector._to_domain(response)

        # Then
        assert result.txid == ['ORDER-001', 'ORDER-002']

    def test_to_domain_handles_validation_response_without_txid(self, mock_client):
        # Given
        connector = AddOrderConnector(client=mock_client)
        validation_response = {'descr': {'order': 'buy 10.00 XBTGBP @ market'}}

        # When
        result = connector._to_domain(validation_response)

        # Then
        assert result.txid is None
        assert result.order_description == 'buy 10.00 XBTGBP @ market'

    def test_place_passes_correct_parameters(self, mock_client):
        # Given
        connector = AddOrderConnector(client=mock_client)
        connector.service = Mock()
        connector.service.add_order.return_value = {
            'txid': ['ORDER-123'], 'descr': {'order': 'test'}}

        # When
        connector.place('XETHZUSD', 'sell', 5.5)

        # Then
        connector.service.add_order.assert_called_once_with('XETHZUSD', 'sell', 5.5, False)

    def test_place_passes_validate_parameter(self, mock_client):
        # Given
        connector = AddOrderConnector(client=mock_client)
        connector.service = Mock()
        connector.service.add_order.return_value = {'descr': {'order': 'buy 10.00 XBTGBP @ market'}}

        # When
        connector.place('XXBTZGBP', 'buy', 10.0, validate=True)

        # Then
        connector.service.add_order.assert_called_once_with('XXBTZGBP', 'buy', 10.0, True)


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

    def test_init_creates_default_client(self):
        # When
        connector = BalanceConnector()

        # Then
        assert connector.client is not None
        assert isinstance(connector.client, KrakenApiClient)

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

    def test_fetch_returns_empty_dict_when_no_balances(self, mock_client):
        # Given
        connector = BalanceConnector(client=mock_client)
        connector.service = Mock()
        connector.service.fetch_balances.return_value = {}

        # When
        result = connector.fetch()

        # Then
        assert result == {}

    def test_fetch_propagates_service_errors(self, mock_client):
        # Given
        connector = BalanceConnector(client=mock_client)
        connector.service = Mock()
        connector.service.fetch_balances.side_effect = KrakenApiResponseError('API Error')

        # When / Then
        with pytest.raises(KrakenApiResponseError, match='API Error'):
            connector.fetch()


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

    def test_init_creates_default_client(self):
        # When
        connector = TickerConnector()

        # Then
        assert connector.client is not None
        assert isinstance(connector.client, KrakenApiClient)

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

    def test_fetch_propagates_service_errors(self, mock_client):
        # Given
        connector = TickerConnector(client=mock_client)
        connector.service = Mock()
        connector.service.fetch_ticker.side_effect = ValueError('Invalid pair')

        # When / Then
        with pytest.raises(ValueError, match='Invalid pair'):
            connector.fetch('INVALID')


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

    def test_init_creates_default_client(self):
        # When
        connector = AssetPairsConnector()

        # Then
        assert connector.client is not None
        assert isinstance(connector.client, KrakenApiClient)

    def test_fetch_calls_service(self, mock_client):
        # Given
        connector = AssetPairsConnector(client=mock_client)
        connector.service = Mock()
        expected_data = {'XXBTZGBP': {'altname': 'BTCGBP'}}
        connector.service.fetch_asset_pairs.return_value = expected_data

        # When
        result = connector.fetch('XXBTZGBP')

        # Then
        connector.service.fetch_asset_pairs.assert_called_once_with('XXBTZGBP')
        assert result == expected_data


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

    def test_init_creates_default_client(self):
        # When
        connector = OhlcConnector()

        # Then
        assert connector.client is not None
        assert isinstance(connector.client, KrakenApiClient)

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

    def test_fetch_passes_all_parameters(self, mock_client):
        # Given
        connector = OhlcConnector(client=mock_client)
        connector.service = Mock()
        connector.service.fetch_ohlc.return_value = []

        # When
        connector.fetch('XETHZUSD', 5, 1704000000)

        # Then
        connector.service.fetch_ohlc.assert_called_once_with('XETHZUSD', 5, 1704000000)

    def test_fetch_propagates_service_errors(self, mock_client):
        # Given
        connector = OhlcConnector(client=mock_client)
        connector.service = Mock()
        connector.service.fetch_ohlc.side_effect = ValueError('Invalid interval')

        # When / Then
        with pytest.raises(ValueError, match='Invalid interval'):
            connector.fetch('XXBTZGBP', -1, 1704067200)
