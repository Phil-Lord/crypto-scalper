import threading

import pytest
from unittest.mock import patch

import exchange_connector.kraken_utils.kraken_auth_utils as _nonce_module
from exchange_connector.kraken_utils.kraken_auth_utils import get_nonce, get_headers


@pytest.mark.exchange_connector
@pytest.mark.kraken_utils
@pytest.mark.kraken_auth_utils
class TestKrakenAuthUtils:
    @pytest.fixture(autouse=True)
    def reset_nonce_state(self):
        '''Reset module-level nonce counter before each test for isolation.'''
        _nonce_module._last_nonce = 0
        yield
        _nonce_module._last_nonce = 0

    def test_get_nonce_returns_string(self):
        # When
        nonce = get_nonce()

        # Then
        assert isinstance(nonce, str)

    def test_get_nonce_returns_nanosecond_timestamp(self):
        # When
        nonce = get_nonce()

        # Then
        # Should be 19 digits (nanoseconds since epoch)
        assert len(nonce) >= 19

    def test_get_nonce_is_strictly_increasing(self):
        # When
        nonce1 = get_nonce()
        nonce2 = get_nonce()

        # Then
        assert int(nonce2) > int(nonce1)

    def test_get_nonce_is_unique_when_called_rapidly(self):
        # When - call in a tight loop where time_ns may return the same value
        nonces = [get_nonce() for _ in range(200)]

        # Then - all values must be unique (no duplicates)
        assert len(set(nonces)) == len(nonces)

    def test_get_nonce_is_strictly_increasing_when_called_rapidly(self):
        # When
        nonces = [int(get_nonce()) for _ in range(200)]

        # Then - every subsequent nonce is strictly greater than the previous
        assert all(nonces[i] < nonces[i + 1] for i in range(len(nonces) - 1))

    def test_get_nonce_is_thread_safe(self):
        # Given
        results = []
        errors = []

        def collect_nonces():
            try:
                for _ in range(50):
                    results.append(get_nonce())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=collect_nonces) for _ in range(10)]

        # When
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Then - 10 threads × 50 nonces = 500 total, all unique, no errors
        assert not errors
        assert len(results) == 500
        assert len(set(results)) == 500

    def test_get_headers_includes_api_key(self):
        # Given
        with patch('exchange_connector.kraken_utils.kraken_auth_utils.os.getenv') as mock_env:
            mock_env.side_effect = lambda key: {
                'KRAKEN_TRADING_API_KEY': 'test_public_key',
                'KRAKEN_TRADING_API_SECRET': 'dGVzdF9wcml2YXRlX2tleQ=='  # base64 encoded
            }[key]

            params = {'nonce': '123456789', 'pair': 'XXBTZGBP'}
            endpoint = '/0/private/Balance'

            # When
            headers = get_headers(params, endpoint)

            # Then
            assert 'API-Key' in headers
            assert headers['API-Key'] == 'test_public_key'

    def test_get_headers_includes_api_sign(self):
        # Given
        with patch('exchange_connector.kraken_utils.kraken_auth_utils.os.getenv') as mock_env:
            mock_env.side_effect = lambda key: {
                'KRAKEN_TRADING_API_KEY': 'test_public_key',
                'KRAKEN_TRADING_API_SECRET': 'dGVzdF9wcml2YXRlX2tleQ=='  # base64 encoded
            }[key]

            params = {'nonce': '123456789', 'pair': 'XXBTZGBP'}
            endpoint = '/0/private/Balance'

            # When
            headers = get_headers(params, endpoint)

            # Then
            assert 'API-Sign' in headers
            assert isinstance(headers['API-Sign'], str)
            assert len(headers['API-Sign']) > 0

    def test_get_headers_raises_when_api_key_missing(self):
        # Given
        with patch('exchange_connector.kraken_utils.kraken_auth_utils.os.getenv') as mock_env:
            mock_env.side_effect = lambda key: {
                'KRAKEN_TRADING_API_KEY': None,
                'KRAKEN_TRADING_API_SECRET': 'dGVzdF9wcml2YXRlX2tleQ==',
            }.get(key)

            # When / Then
            with pytest.raises(ValueError, match='Kraken API keys are not set'):
                get_headers({'nonce': '123'}, '/0/private/Balance')

    def test_get_headers_raises_when_api_secret_missing(self):
        # Given
        with patch('exchange_connector.kraken_utils.kraken_auth_utils.os.getenv') as mock_env:
            mock_env.side_effect = lambda key: {
                'KRAKEN_TRADING_API_KEY': 'test_public_key',
                'KRAKEN_TRADING_API_SECRET': None,
            }.get(key)

            # When / Then
            with pytest.raises(ValueError, match='Kraken API keys are not set'):
                get_headers({'nonce': '123'}, '/0/private/Balance')
