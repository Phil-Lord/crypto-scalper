import threading

import pytest
from unittest.mock import Mock, patch

from exchange_connector.api.exceptions import (
    KrakenTooManyRequestsError,
    KrakenApiResponseError,
    KrakenNetworkError,
    KrakenParseError,
)
from exchange_connector.api.kraken_api_client import KrakenApiClient


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
            params = {'pair': 'XXBTZGBP'}

            # When
            result = client.make_request('POST', '/0/private/Balance', params)

            # Then
            assert result == mock_response
            call_args = mock_headers.call_args[0]
            assert call_args[0]['pair'] == 'XXBTZGBP'
            assert 'nonce' in call_args[0]
            assert call_args[1] == '/0/private/Balance'

    def test_make_request_raises_network_error_on_request_failure(self, client):
        # Given
        import requests
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.RequestException('Connection failed')

            # When / Then
            with pytest.raises(KrakenNetworkError, match='Error making request'):
                client.make_request('GET', '/0/public/Ticker', {'pair': 'XXBTZGBP'})

    def test_make_request_raises_parse_error_on_json_parse_failure(self, client):
        # Given
        with patch('requests.get') as mock_get:
            mock_get.return_value = Mock(
                json=Mock(side_effect=ValueError('Invalid JSON')),
                raise_for_status=Mock()
            )

            # When / Then
            with pytest.raises(KrakenParseError, match='Failed to parse JSON'):
                client.make_request('GET', '/0/public/Ticker', {'pair': 'XXBTZGBP'})

    def test_make_request_constructs_correct_url_for_get(self, client, mock_response):
        # Given
        with patch('requests.get') as mock_get:
            mock_get.return_value = Mock(
                json=Mock(return_value=mock_response),
                raise_for_status=Mock()
            )

            # When
            client.make_request('GET', '/0/public/Time', {})

            # Then
            expected_url = 'https://api.kraken.com/0/public/Time'
            assert mock_get.call_args[0][0] == expected_url

    def test_make_request_constructs_correct_url_for_post(self, client, mock_response):
        # Given
        with patch('requests.post') as mock_post, \
                patch('exchange_connector.api.kraken_api_client.get_headers') as mock_headers:
            mock_post.return_value = Mock(
                json=Mock(return_value=mock_response),
                raise_for_status=Mock()
            )
            mock_headers.return_value = {'API-Key': 'key', 'API-Sign': 'sign'}

            # When
            client.make_request('POST', '/0/private/Balance', {})

            # Then
            expected_url = 'https://api.kraken.com/0/private/Balance'
            assert mock_post.call_args[0][0] == expected_url

    def test_make_request_passes_params_as_query_for_get(self, client, mock_response):
        # Given
        with patch('requests.get') as mock_get:
            mock_get.return_value = Mock(
                json=Mock(return_value=mock_response),
                raise_for_status=Mock()
            )
            params = {'pair': 'XXBTZGBP', 'since': '123456'}

            # When
            client.make_request('GET', '/0/public/Ticker', params)

            # Then
            assert mock_get.call_args[1]['params'] == params

    def test_make_request_passes_params_as_data_for_post(self, client, mock_response):
        # Given
        with patch('requests.post') as mock_post, \
                patch('exchange_connector.api.kraken_api_client.get_headers') as mock_headers:
            mock_post.return_value = Mock(
                json=Mock(return_value=mock_response),
                raise_for_status=Mock()
            )
            mock_headers.return_value = {'API-Key': 'key', 'API-Sign': 'sign'}
            params = {'pair': 'XXBTZGBP'}

            # When
            client.make_request('POST', '/0/private/AddOrder', params)

            # Then
            post_data = mock_post.call_args[1]['data']
            assert post_data['pair'] == 'XXBTZGBP'
            assert 'nonce' in post_data
            assert params == {'pair': 'XXBTZGBP'}  # original not mutated

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

    def test_handle_errors_raises_api_response_error_for_other_errors(self, client):
        # Given
        response = {'error': ['EOrder:Insufficient funds']}

        # When / Then
        with pytest.raises(KrakenApiResponseError, match='API Error'):
            client._handle_errors(response)

    def test_handle_errors_does_nothing_when_no_error_key(self, client):
        # Given
        response = {'result': {'data': 'value'}}

        # When / Then (no exception raised)
        client._handle_errors(response)

    def test_handle_errors_raises_on_multiple_errors(self, client):
        # Given
        response = {'error': ['EOrder:Insufficient funds', 'EGeneral:Invalid nonce']}

        # When / Then
        with pytest.raises(KrakenApiResponseError, match='API Error'):
            client._handle_errors(response)

    def test_make_request_calls_raise_for_status(self, client, mock_response):
        # Given
        with patch('requests.get') as mock_get:
            mock_status = Mock()
            mock_get.return_value = Mock(
                json=Mock(return_value=mock_response),
                raise_for_status=mock_status
            )

            # When
            client.make_request('GET', '/0/public/Ticker', {'pair': 'XXBTZGBP'})

            # Then
            mock_status.assert_called_once()

    def test_make_request_raises_value_error_on_unsupported_method(self, client):
        # Given / When / Then
        with pytest.raises(ValueError, match='Unsupported HTTP method: DELETE'):
            client.make_request('DELETE', '/0/public/Ticker', {})

    def test_make_request_post_injects_nonce(self, client, mock_response):
        # Given
        with patch('requests.post') as mock_post, \
                patch('exchange_connector.api.kraken_api_client.get_headers') as mock_headers:
            mock_post.return_value = Mock(
                json=Mock(return_value=mock_response),
                raise_for_status=Mock()
            )
            mock_headers.return_value = {'API-Key': 'key', 'API-Sign': 'sign'}

            # When - caller passes no nonce
            client.make_request('POST', '/0/private/Balance', {})

            # Then - client injected a nanosecond timestamp nonce
            data_sent = mock_post.call_args[1]['data']
            assert 'nonce' in data_sent
            assert len(data_sent['nonce']) >= 19

    def test_make_request_get_does_not_inject_nonce(self, client, mock_response):
        # Given
        with patch('requests.get') as mock_get:
            mock_get.return_value = Mock(
                json=Mock(return_value=mock_response),
                raise_for_status=Mock()
            )
            params = {'pair': 'XXBTZGBP'}

            # When
            client.make_request('GET', '/0/public/Ticker', params)

            # Then - nonce must not be added to public GET requests
            assert 'nonce' not in mock_get.call_args[1]['params']

    def test_make_request_post_nonces_are_ordered_under_concurrency(self, mock_response):
        # Given - capture nonces in the order they reach requests.post
        # Each time a thread calls requests.post, we record the nonce from the data dict;
        # this is the nonce as received by the socket (dispatch order, not assignment order).

        nonces_received = []

        def capture_post(url, data, headers):
            nonces_received.append(int(data['nonce']))
            return Mock(json=Mock(return_value=mock_response), raise_for_status=Mock())

        with patch('requests.post', side_effect=capture_post), \
                patch('exchange_connector.api.kraken_api_client.get_headers') as mock_headers:
            mock_headers.return_value = {'API-Key': 'key', 'API-Sign': 'sign'}
            client = KrakenApiClient()
            threads = [
                threading.Thread(target=client.make_request,
                                 args=('POST', '/0/private/Balance', {}))
                for _ in range(20)
            ]

            # When
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Then - every nonce dispatched is strictly greater than the previous
            assert len(nonces_received) == 20
            assert all(nonces_received[i] < nonces_received[i + 1] for i in range(19))


@pytest.mark.exchange_connector
@pytest.mark.api
@pytest.mark.kraken_api_client
class TestNextNonce:
    @pytest.fixture(autouse=True)
    def reset_last_nonce(self):
        KrakenApiClient._last_nonce = 0
        yield
        KrakenApiClient._last_nonce = 0

    def test_returns_string(self):
        nonce = KrakenApiClient()._next_nonce()
        assert isinstance(nonce, str)

    def test_returns_nanosecond_precision(self):
        nonce = KrakenApiClient()._next_nonce()
        assert len(nonce) >= 19

    def test_successive_calls_are_strictly_increasing(self):
        client = KrakenApiClient()
        nonce1 = int(client._next_nonce())
        nonce2 = int(client._next_nonce())
        assert nonce2 > nonce1

    def test_uses_increment_when_clock_is_frozen(self):
        # When time.time_ns() returns the same value on every call, nonce still strictly increases
        fixed_time = 1_000_000_000_000_000_000
        client = KrakenApiClient()
        with patch('time.time_ns', return_value=fixed_time):
            nonce1 = int(client._next_nonce())
            nonce2 = int(client._next_nonce())
        assert nonce1 == fixed_time
        assert nonce2 == fixed_time + 1

    def test_uses_increment_when_clock_goes_backwards(self):
        # When time.time_ns() goes backwards (NTP adjustment), nonce still strictly increases
        client = KrakenApiClient()
        future_time = 2_000_000_000_000_000_000
        with patch('time.time_ns', return_value=future_time):
            first = int(client._next_nonce())
        past_time = 1_000_000_000_000_000_000
        with patch('time.time_ns', return_value=past_time):
            second = int(client._next_nonce())
        assert first == future_time
        assert second == future_time + 1


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


@pytest.mark.exchange_connector
@pytest.mark.api
class TestKrakenApiErrorHierarchy:
    def test_all_kraken_errors_inherit_from_base(self):
        # Given
        from exchange_connector.api.exceptions import KrakenApiError

        # When / Then
        assert issubclass(KrakenTooManyRequestsError, KrakenApiError)
        assert issubclass(KrakenApiResponseError, KrakenApiError)
        assert issubclass(KrakenNetworkError, KrakenApiError)
        assert issubclass(KrakenParseError, KrakenApiError)

    def test_can_catch_all_kraken_errors_with_base_class(self):
        # Given
        from exchange_connector.api.exceptions import KrakenApiError

        # When / Then - Rate limit error
        try:
            raise KrakenTooManyRequestsError()
        except KrakenApiError:
            pass  # Successfully caught

        # When / Then - API response error
        try:
            raise KrakenApiResponseError('Test error')
        except KrakenApiError:
            pass  # Successfully caught

        # When / Then - Network error
        try:
            raise KrakenNetworkError('Network failed')
        except KrakenApiError:
            pass  # Successfully caught

        # When / Then - Parse error
        try:
            raise KrakenParseError('Parse failed')
        except KrakenApiError:
            pass  # Successfully caught

    def test_can_catch_specific_error_types(self):
        # When / Then
        with pytest.raises(KrakenTooManyRequestsError):
            raise KrakenTooManyRequestsError()

        with pytest.raises(KrakenApiResponseError):
            raise KrakenApiResponseError('API error')

        with pytest.raises(KrakenNetworkError):
            raise KrakenNetworkError('Network error')

        with pytest.raises(KrakenParseError):
            raise KrakenParseError('Parse error')
