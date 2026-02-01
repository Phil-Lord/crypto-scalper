import pytest
from unittest.mock import Mock, patch

from exchange_connector.services.kraken_service import KrakenService
from exchange_connector.api.kraken_api_client import KrakenApiClient


@pytest.mark.exchange_connector
@pytest.mark.services
@pytest.mark.kraken_service
class TestKrakenService:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    @pytest.fixture
    def service(self, mock_client):
        return KrakenService(mock_client)

    def test_init_stores_client(self, mock_client):
        # When
        service = KrakenService(mock_client)

        # Then
        assert service.client == mock_client

    def test_make_request_returns_result(self, service, mock_client):
        # Given
        mock_client.make_request.return_value = {
            'result': {'XXBTZGBP': {'a': ['50000']}},
            'error': []
        }

        # When
        result = service.make_request('GET', '/0/public/Ticker', {'pair': 'XXBTZGBP'})

        # Then
        assert result == {'XXBTZGBP': {'a': ['50000']}}

    def test_validate_pair_raises_on_empty_pair(self, service):
        # When / Then
        with pytest.raises(ValueError, match='cannot be empty'):
            service.validate_pair('')

    def test_validate_pair_raises_on_none_pair(self, service):
        # When / Then
        with pytest.raises(ValueError, match='cannot be empty'):
            service.validate_pair(None)

    def test_validate_pair_raises_on_short_pair(self, service):
        # When / Then
        with pytest.raises(ValueError, match='Invalid trading pair'):
            service.validate_pair('BTC')

    def test_validate_pair_accepts_valid_pair(self, service):
        # When / Then (no exception raised)
        service.validate_pair('XXBTZGBP')


@pytest.mark.exchange_connector
@pytest.mark.services
@pytest.mark.add_order_service
class TestAddOrderService:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    def test_add_order_buy_includes_viqc_flag(self, mock_client):
        # Given
        from exchange_connector.services.add_order_service import AddOrderService
        service = AddOrderService(mock_client)
        mock_client.make_request.return_value = {'result': {'txid': ['ORDER-123']}, 'error': []}

        with patch('exchange_connector.services.add_order_service.get_nonce', return_value='123456'):
            # When
            service.add_order('XXBTZGBP', 'buy', 100.0)

            # Then
            call_args = mock_client.make_request.call_args
            params = call_args[0][2]
            assert params['oflags'] == 'viqc'

    def test_add_order_sell_does_not_include_viqc_flag(self, mock_client):
        # Given
        from exchange_connector.services.add_order_service import AddOrderService
        service = AddOrderService(mock_client)
        mock_client.make_request.return_value = {'result': {'txid': ['ORDER-123']}, 'error': []}

        with patch('exchange_connector.services.add_order_service.get_nonce', return_value='123456'):
            # When
            service.add_order('XXBTZGBP', 'sell', 0.001)

            # Then
            call_args = mock_client.make_request.call_args
            params = call_args[0][2]
            assert 'oflags' not in params


@pytest.mark.exchange_connector
@pytest.mark.services
@pytest.mark.ticker_service
class TestTickerService:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    def test_fetch_ticker_returns_pair_data(self, mock_client):
        # Given
        from exchange_connector.services.ticker_service import TickerService
        service = TickerService(mock_client)
        mock_client.make_request.return_value = {
            'result': {'XXBTZGBP': {'a': ['50000'], 'b': ['49999']}},
            'error': []
        }

        # When
        result = service.fetch_ticker('XXBTZGBP')

        # Then
        assert result == {'a': ['50000'], 'b': ['49999']}


@pytest.mark.exchange_connector
@pytest.mark.services
@pytest.mark.balance_service
class TestBalanceService:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    def test_fetch_balances_uses_post(self, mock_client):
        # Given
        from exchange_connector.services.balance_service import BalanceService
        service = BalanceService(mock_client)
        mock_client.make_request.return_value = {'result': {'XXBT': '1.5'}, 'error': []}

        with patch('exchange_connector.services.balance_service.get_nonce', return_value='123456'):
            # When
            service.fetch_balances()

            # Then
            call_args = mock_client.make_request.call_args
            assert call_args[0][0] == 'POST'


@pytest.mark.exchange_connector
@pytest.mark.services
@pytest.mark.asset_pairs_service
class TestAssetPairsService:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    def test_fetch_asset_pairs_validates_pair(self, mock_client):
        # Given
        from exchange_connector.services.asset_pairs_service import AssetPairsService
        service = AssetPairsService(mock_client)

        # When / Then
        with pytest.raises(ValueError, match='cannot be empty'):
            service.fetch_asset_pairs('')


@pytest.mark.exchange_connector
@pytest.mark.services
@pytest.mark.ohlc_service
class TestOhlcService:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    def test_fetch_ohlc_returns_pair_data(self, mock_client):
        # Given
        from exchange_connector.services.ohlc_service import OhlcService
        service = OhlcService(mock_client)
        ohlc_data = [[1704067200, '50000', '50100', '49900', '50050', '100', '5000000', 10]]
        mock_client.make_request.return_value = {
            'result': {'XXBTZGBP': ohlc_data, 'last': 1704067200},
            'error': []
        }

        # When
        result = service.fetch_ohlc('XXBTZGBP', 1, 1704067200)

        # Then
        assert result == ohlc_data


@pytest.mark.exchange_connector
@pytest.mark.services
@pytest.mark.trades_service
class TestTradesService:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    def test_fetch_trades_validates_pair(self, mock_client):
        # Given
        from exchange_connector.services.trades_service import TradesService
        service = TradesService(mock_client)

        # When / Then
        with pytest.raises(ValueError, match='cannot be empty'):
            service.fetch_trades('', 1704067200000000000, 1704153600000000000)
