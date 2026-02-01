import pytest
from unittest.mock import Mock, patch

from exchange_connector.api.kraken_api_client import KrakenApiClient
from exchange_connector.api.exceptions import KrakenTooManyRequestsError


@pytest.mark.exchange_connector
@pytest.mark.api
@pytest.mark.kraken_api_client
class TestKrakenApiClient:
    @pytest.fixture
    def client(self):
        return KrakenApiClient()

    @pytest.fixture
    def mock_response(self):
        return {'result': {'XXBTZGBP': {'a': ['50000.0']}}, 'error': []}

    def test_make_request_get_returns_json(self, client, mock_response):
        # Given
        with patch('requests.get') as mock_get:
            mock_get.return_value = Mock(
                json=Mock(return_value=mock_response),
                raise_for_status=Mock()
            )

            # When
            result = client.make_request('GET', '/0/public/Ticker', {'pair': 'XXBTZGBP'})

            # Then
            assert result == mock_response
            mock_get.assert_called_once()

    def test_make_request_post_includes_auth_headers(self, client, mock_response):
        # Given
        with patch('requests.post') as mock_post, \
                patch('exchange_connector.api.kraken_api_client.get_headers') as mock_headers:
            mock_post.return_value = Mock(
                json=Mock(return_value=mock_response),
                raise_for_status=Mock()
            )
            mock_headers.return_value = {'API-Key': 'key', 'API-Sign': 'sign'}
            params = {'nonce': '123', 'pair': 'XXBTZGBP'}

            # When
            result = client.make_request('POST', '/0/private/Balance', params)

            # Then
            assert result == mock_response
            mock_headers.assert_called_once_with(params, '/0/private/Balance')

    def test_make_request_raises_runtime_error_on_request_failure(self, client):
        # Given
        import requests
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.RequestException('Connection failed')

            # When / Then
            with pytest.raises(RuntimeError, match='Error making request'):
                client.make_request('GET', '/0/public/Ticker', {'pair': 'XXBTZGBP'})

    def test_make_request_raises_runtime_error_on_json_parse_failure(self, client):
        # Given
        with patch('requests.get') as mock_get:
            mock_get.return_value = Mock(
                json=Mock(side_effect=ValueError('Invalid JSON')),
                raise_for_status=Mock()
            )

            # When / Then
            with pytest.raises(RuntimeError, match='Failed to parse JSON'):
                client.make_request('GET', '/0/public/Ticker', {'pair': 'XXBTZGBP'})

    def test_handle_errors_does_nothing_on_empty_error_list(self, client):
        # Given
        response = {'result': {'data': 'value'}, 'error': []}

        # When / Then (no exception raised)
        client._handle_errors(response)

    def test_handle_errors_raises_too_many_requests_error(self, client):
        # Given
        response = {'error': ['EGeneral:Too many requests']}

        # When / Then
        with pytest.raises(KrakenTooManyRequestsError):
            client._handle_errors(response)

    def test_handle_errors_raises_runtime_error_for_other_errors(self, client):
        # Given
        response = {'error': ['EOrder:Insufficient funds']}

        # When / Then
        with pytest.raises(RuntimeError, match='API Error'):
            client._handle_errors(response)


@pytest.mark.exchange_connector
@pytest.mark.api
@pytest.mark.kraken_too_many_requests_error
class TestKrakenTooManyRequestsError:
    def test_exception_has_message(self):
        # When
        error = KrakenTooManyRequestsError()

        # Then
        assert 'rate limit' in str(error).lower()

    def test_exception_is_instance_of_exception(self):
        # When
        error = KrakenTooManyRequestsError()

        # Then
        assert isinstance(error, Exception)
