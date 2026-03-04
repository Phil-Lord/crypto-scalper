import pytest
from unittest.mock import Mock, patch

from tenacity import RetryError

from exchange_connector.services.kraken_service import KrakenService
from exchange_connector.api.kraken_api_client import KrakenApiClient
from exchange_connector.api.exceptions import (
    KrakenTooManyRequestsError,
    KrakenApiResponseError,
)


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

    def test_make_request_retries_on_rate_limit(self, service, mock_client):
        # Given
        mock_client.make_request.side_effect = [
            KrakenTooManyRequestsError(),
            KrakenTooManyRequestsError(),
            {'result': {'data': 'success'}, 'error': []}
        ]

        # When
        with patch('time.sleep'):  # Mock sleep to make retries instant
            result = service.make_request('GET', '/0/public/Ticker', {'pair': 'XXBTZGBP'})

        # Then
        assert result == {'data': 'success'}
        assert mock_client.make_request.call_count == 3

    def test_make_request_fails_after_max_retries(self, service, mock_client):
        # Given
        mock_client.make_request.side_effect = KrakenTooManyRequestsError()

        # When / Then
        with patch('time.sleep'):  # Mock sleep to make retries instant
            with pytest.raises(RetryError):
                service.make_request('GET', '/0/public/Ticker', {'pair': 'XXBTZGBP'})

        # Should retry 5 times
        assert mock_client.make_request.call_count == 5

    def test_make_request_does_not_retry_on_other_errors(self, service, mock_client):
        # Given
        mock_client.make_request.side_effect = KrakenApiResponseError('API Error')

        # When / Then
        with pytest.raises(KrakenApiResponseError, match='API Error'):
            service.make_request('GET', '/0/public/Ticker', {'pair': 'XXBTZGBP'})

        # Should not retry on non-rate-limit errors
        assert mock_client.make_request.call_count == 1

    def test_make_request_logs_retry_attempts(self, service, mock_client, caplog):
        # Given
        mock_client.make_request.side_effect = [
            KrakenTooManyRequestsError(),
            {'result': {'data': 'success'}, 'error': []}
        ]

        # When
        with patch('time.sleep'):
            import logging
            caplog.set_level(logging.DEBUG)
            result = service.make_request('GET', '/0/public/Ticker', {'pair': 'XXBTZGBP'})

        # Then
        assert result == {'data': 'success'}

        # Should log before and after retry attempts at DEBUG level
        log_messages = [record.message for record in caplog.records]
        assert any('Starting call' in message for message in log_messages)
        assert any('Finished call' in message for message in log_messages)

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
        with pytest.raises(ValueError, match='Invalid trading pair format'):
            service.validate_pair('BTC')

    def test_validate_pair_raises_on_non_string_pair(self, service):
        # When / Then
        with pytest.raises(ValueError, match='must be a string'):
            service.validate_pair(12345)

    def test_validate_pair_raises_on_lowercase_pair(self, service):
        # When / Then
        with pytest.raises(ValueError, match='Invalid trading pair format'):
            service.validate_pair('xxbtzgbp')

    def test_validate_pair_raises_on_mixed_case_pair(self, service):
        # When / Then
        with pytest.raises(ValueError, match='Invalid trading pair format'):
            service.validate_pair('XxBtZgBp')

    def test_validate_pair_raises_on_special_characters(self, service):
        # When / Then
        with pytest.raises(ValueError, match='Invalid trading pair format'):
            service.validate_pair('XBT-GBP')

    def test_validate_pair_raises_on_too_long_pair(self, service):
        # When / Then
        with pytest.raises(ValueError, match='Invalid trading pair format'):
            service.validate_pair('XXBTZGBPEXTRA')

    def test_validate_pair_accepts_valid_pair(self, service):
        # When / Then (no exception raised)
        service.validate_pair('XXBTZGBP')

    def test_validate_pair_accepts_six_char_pair(self, service):
        # When / Then
        service.validate_pair('ADAUSD')

    def test_validate_pair_accepts_pair_with_numbers(self, service):
        # When / Then
        service.validate_pair('ADA2USD')

    def test_validate_pair_accepts_twelve_char_pair(self, service):
        # When / Then
        service.validate_pair('XXBTZGBPLONG')


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

    def test_add_order_validates_pair(self, mock_client):
        # Given
        from exchange_connector.services.add_order_service import AddOrderService
        service = AddOrderService(mock_client)

        # When / Then
        with pytest.raises(ValueError, match='cannot be empty'):
            service.add_order('', 'buy', 100.0)

    def test_add_order_includes_correct_params(self, mock_client):
        # Given
        from exchange_connector.services.add_order_service import AddOrderService
        service = AddOrderService(mock_client)
        mock_client.make_request.return_value = {'result': {'txid': ['ORDER-123']}, 'error': []}

        with patch('exchange_connector.services.add_order_service.get_nonce', return_value='987654'):
            # When
            service.add_order('XXBTZGBP', 'buy', 50.0)

            # Then
            call_args = mock_client.make_request.call_args
            params = call_args[0][2]
            assert params['pair'] == 'XXBTZGBP'
            assert params['type'] == 'buy'
            assert params['volume'] == 50.0
            assert params['ordertype'] == 'market'
            assert params['nonce'] == '987654'

    def test_add_order_uses_post_method(self, mock_client):
        # Given
        from exchange_connector.services.add_order_service import AddOrderService
        service = AddOrderService(mock_client)
        mock_client.make_request.return_value = {'result': {'txid': ['ORDER-123']}, 'error': []}

        with patch('exchange_connector.services.add_order_service.get_nonce', return_value='123456'):
            # When
            service.add_order('XXBTZGBP', 'sell', 0.5)

            # Then
            call_args = mock_client.make_request.call_args
            assert call_args[0][0] == 'POST'
            assert call_args[0][1] == '/0/private/AddOrder'

    def test_add_order_includes_validate_false_by_default(self, mock_client):
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
            assert params['validate'] is False

    def test_add_order_includes_validate_true_when_specified(self, mock_client):
        # Given
        from exchange_connector.services.add_order_service import AddOrderService
        service = AddOrderService(mock_client)
        mock_client.make_request.return_value = {
            'result': {'descr': {'order': 'test'}}, 'error': []}

        with patch('exchange_connector.services.add_order_service.get_nonce', return_value='123456'):
            # When
            service.add_order('XXBTZGBP', 'buy', 100.0, validate=True)

            # Then
            call_args = mock_client.make_request.call_args
            params = call_args[0][2]
            assert params['validate'] is True


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

    def test_fetch_ticker_validates_pair(self, mock_client):
        # Given
        from exchange_connector.services.ticker_service import TickerService
        service = TickerService(mock_client)

        # When / Then
        with pytest.raises(ValueError, match='cannot be empty'):
            service.fetch_ticker('')

    def test_fetch_ticker_uses_get_method(self, mock_client):
        # Given
        from exchange_connector.services.ticker_service import TickerService
        service = TickerService(mock_client)
        mock_client.make_request.return_value = {
            'result': {'XXBTZGBP': {'a': ['50000']}},
            'error': []
        }

        # When
        service.fetch_ticker('XXBTZGBP')

        # Then
        call_args = mock_client.make_request.call_args
        assert call_args[0][0] == 'GET'
        assert call_args[0][1] == '/0/public/Ticker'
        assert call_args[0][2] == {'pair': 'XXBTZGBP'}


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

    def test_fetch_balances_includes_nonce(self, mock_client):
        # Given
        from exchange_connector.services.balance_service import BalanceService
        service = BalanceService(mock_client)
        mock_client.make_request.return_value = {'result': {'XXBT': '1.5'}, 'error': []}

        with patch('exchange_connector.services.balance_service.get_nonce', return_value='999888'):
            # When
            service.fetch_balances()

            # Then
            call_args = mock_client.make_request.call_args
            params = call_args[0][2]
            assert params['nonce'] == '999888'

    def test_fetch_balances_returns_balance_dict(self, mock_client):
        # Given
        from exchange_connector.services.balance_service import BalanceService
        service = BalanceService(mock_client)
        expected_balances = {'XXBT': '1.5', 'ZGBP': '5000.0', 'XETH': '10.0'}
        mock_client.make_request.return_value = {'result': expected_balances, 'error': []}

        with patch('exchange_connector.services.balance_service.get_nonce', return_value='123456'):
            # When
            result = service.fetch_balances()

            # Then
            assert result == expected_balances


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

    def test_fetch_asset_pairs_returns_pair_info(self, mock_client):
        # Given
        from exchange_connector.services.asset_pairs_service import AssetPairsService
        service = AssetPairsService(mock_client)
        expected_result = {
            'XXBTZGBP': {
                'altname': 'BTCGBP',
                'wsname': 'XBT/GBP',
                'pair_decimals': 1
            }
        }
        mock_client.make_request.return_value = {'result': expected_result, 'error': []}

        # When
        result = service.fetch_asset_pairs('XXBTZGBP')

        # Then
        assert result == expected_result

    def test_fetch_asset_pairs_uses_get_method(self, mock_client):
        # Given
        from exchange_connector.services.asset_pairs_service import AssetPairsService
        service = AssetPairsService(mock_client)
        mock_client.make_request.return_value = {'result': {}, 'error': []}

        # When
        service.fetch_asset_pairs('XXBTZGBP')

        # Then
        call_args = mock_client.make_request.call_args
        assert call_args[0][0] == 'GET'
        assert call_args[0][1] == '/0/public/AssetPairs'


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

    def test_fetch_ohlc_validates_pair(self, mock_client):
        # Given
        from exchange_connector.services.ohlc_service import OhlcService
        service = OhlcService(mock_client)

        # When / Then
        with pytest.raises(ValueError, match='cannot be empty'):
            service.fetch_ohlc('', 1, 1704067200)

    def test_fetch_ohlc_uses_correct_params(self, mock_client):
        # Given
        from exchange_connector.services.ohlc_service import OhlcService
        service = OhlcService(mock_client)
        ohlc_data = [[1704067200, '50000', '50100', '49900', '50050', '100', '5000000', 10]]
        mock_client.make_request.return_value = {
            'result': {'XXBTZGBP': ohlc_data, 'last': 1704067200},
            'error': []
        }

        # When
        service.fetch_ohlc('XXBTZGBP', 5, 1704000000)

        # Then
        call_args = mock_client.make_request.call_args
        assert call_args[0][0] == 'GET'
        assert call_args[0][1] == '/0/public/OHLC'
        params = call_args[0][2]
        assert params['pair'] == 'XXBTZGBP'
        assert params['interval'] == 5
        assert params['since'] == 1704000000


@pytest.mark.exchange_connector
@pytest.mark.services
@pytest.mark.trades_service
class TestTradesService:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    @pytest.fixture
    def sample_trade_batch(self):
        return [
            ['50000.0', '0.001', 1704067200.123, 'b', 'm', '', 123456789],
            ['50001.0', '0.002', 1704067201.456, 's', 'l', '', 123456790],
            'last_timestamp_placeholder'
        ]

    def test_fetch_trades_validates_pair(self, mock_client):
        # Given
        from exchange_connector.services.trades_service import TradesService
        service = TradesService(mock_client)

        # When / Then
        with pytest.raises(ValueError, match='cannot be empty'):
            service.fetch_trades('', 1704067200000000000, 1704153600000000000)

    def test_fetch_trades_paginates_single_page(self, mock_client, sample_trade_batch):
        # Given
        from exchange_connector.services.trades_service import TradesService
        service = TradesService(mock_client)
        start = 1704067200000000000
        end = 1704067300000000000

        # Mock single page response
        mock_client.make_request.return_value = {
            'result': {
                'XXBTZGBP': sample_trade_batch,
                'last': str(end)
            }
        }

        # When
        trades = service.fetch_trades('XXBTZGBP', start, end)

        # Then
        assert len(trades) == 2  # Excludes the 'last_timestamp_placeholder'
        mock_client.make_request.assert_called_once()

    def test_fetch_trades_paginates_multiple_pages(self, mock_client):
        # Given
        from exchange_connector.services.trades_service import TradesService
        service = TradesService(mock_client)
        start = 1704067200000000000
        mid = 1704067250000000000
        end = 1704067300000000000

        # Mock two pages of responses
        page1 = [
            ['50000.0', '0.001', 1704067200.123, 'b', 'm', '', 1],
            'placeholder'
        ]
        page2 = [
            ['50100.0', '0.002', 1704067250.456, 's', 'l', '', 2],
            'placeholder'
        ]

        mock_client.make_request.side_effect = [
            {'result': {'XXBTZGBP': page1, 'last': str(mid)}},
            {'result': {'XXBTZGBP': page2, 'last': str(end)}}
        ]

        # When
        trades = service.fetch_trades('XXBTZGBP', start, end)

        # Then
        assert len(trades) == 2
        assert mock_client.make_request.call_count == 2

        # Verify pagination params
        first_call = mock_client.make_request.call_args_list[0]
        second_call = mock_client.make_request.call_args_list[1]
        assert first_call[0][2]['since'] == start
        assert second_call[0][2]['since'] == mid

    def test_fetch_trades_updates_since_parameter(self, mock_client):
        # Given
        from exchange_connector.services.trades_service import TradesService
        service = TradesService(mock_client)
        start = 1000000000000000000
        mid1 = 1000000001000000000
        mid2 = 1000000002000000000
        end = 1000000003000000000

        mock_client.make_request.side_effect = [
            {'result': {'XXBTZGBP': [['50000.0', '0.001', 1.0,
                                      'b', 'm', '', 1], 'p'], 'last': str(mid1)}},
            {'result': {'XXBTZGBP': [['50100.0', '0.002', 2.0,
                                      's', 'l', '', 2], 'p'], 'last': str(mid2)}},
            {'result': {'XXBTZGBP': [['50200.0', '0.003', 3.0,
                                      'b', 'm', '', 3], 'p'], 'last': str(end)}}
        ]

        # When
        trades = service.fetch_trades('XXBTZGBP', start, end)

        # Then
        assert len(trades) == 3
        assert mock_client.make_request.call_count == 3

    def test_fetch_trades_validates_invalid_pair_format(self, mock_client):
        # Given
        from exchange_connector.services.trades_service import TradesService
        service = TradesService(mock_client)

        # When / Then
        with pytest.raises(ValueError, match='Invalid trading pair'):
            service.fetch_trades('BTC', 1704067200000000000, 1704153600000000000)


@pytest.mark.exchange_connector
@pytest.mark.services
@pytest.mark.query_orders_service
class TestQueryOrdersService:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    def test_fetch_orders_uses_post_method(self, mock_client):
        # Given
        from exchange_connector.services.query_orders_service import QueryOrdersService
        service = QueryOrdersService(mock_client)
        mock_client.make_request.return_value = {
            'result': {'ORDER-123': {'price': '50000.0', 'vol_exec': '0.001', 'fee': '0.5'}},
            'error': []
        }

        # When
        service.fetch_orders('ORDER-123')

        # Then
        call_args = mock_client.make_request.call_args
        assert call_args[0][0] == 'POST'

    def test_fetch_orders_uses_correct_endpoint(self, mock_client):
        # Given
        from exchange_connector.services.query_orders_service import QueryOrdersService
        service = QueryOrdersService(mock_client)
        mock_client.make_request.return_value = {
            'result': {'ORDER-123': {'price': '50000.0', 'vol_exec': '0.001', 'fee': '0.5'}},
            'error': []
        }

        # When
        service.fetch_orders('ORDER-123')

        # Then
        call_args = mock_client.make_request.call_args
        assert call_args[0][1] == '/0/private/QueryOrders'

    def test_fetch_orders_passes_txid_as_param(self, mock_client):
        # Given
        from exchange_connector.services.query_orders_service import QueryOrdersService
        service = QueryOrdersService(mock_client)
        mock_client.make_request.return_value = {
            'result': {'ORDER-456': {'price': '49000.0', 'vol_exec': '0.002', 'fee': '0.3'}},
            'error': []
        }

        # When
        with patch('exchange_connector.services.query_orders_service.get_nonce', return_value='123456'):
            service.fetch_orders('ORDER-456')

        # Then
        call_args = mock_client.make_request.call_args
        params = call_args[0][2]
        assert params['txid'] == 'ORDER-456'

    def test_fetch_orders_includes_nonce(self, mock_client):
        # Given
        from exchange_connector.services.query_orders_service import QueryOrdersService
        service = QueryOrdersService(mock_client)
        mock_client.make_request.return_value = {
            'result': {'ORDER-789': {'price': '48000.0', 'vol_exec': '0.003', 'fee': '0.2'}},
            'error': []
        }

        # When
        with patch('exchange_connector.services.query_orders_service.get_nonce', return_value='999888'):
            service.fetch_orders('ORDER-789')

        # Then
        call_args = mock_client.make_request.call_args
        params = call_args[0][2]
        assert params['nonce'] == '999888'

    def test_fetch_orders_returns_result(self, mock_client):
        # Given
        from exchange_connector.services.query_orders_service import QueryOrdersService
        service = QueryOrdersService(mock_client)
        order_data = {'price': '50000.0', 'vol_exec': '0.001', 'fee': '0.5'}
        mock_client.make_request.return_value = {
            'result': {'ORDER-123': order_data},
            'error': []
        }

        # When
        result = service.fetch_orders('ORDER-123')

        # Then
        assert result == {'ORDER-123': order_data}
