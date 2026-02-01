import pytest
from unittest.mock import patch

from exchange_connector.kraken_utils.kraken_auth_utils import get_nonce, get_headers


@pytest.mark.exchange_connector
@pytest.mark.kraken_utils
@pytest.mark.kraken_auth_utils
class TestKrakenAuthUtils:
    def test_get_nonce_returns_string(self):
        # When
        nonce = get_nonce()

        # Then
        assert isinstance(nonce, str)

    def test_get_nonce_returns_millisecond_timestamp(self):
        # When
        nonce = get_nonce()

        # Then
        # Should be 13 digits (milliseconds since epoch)
        assert len(nonce) >= 13

    def test_get_nonce_is_increasing(self):
        # When
        nonce1 = get_nonce()
        nonce2 = get_nonce()

        # Then
        assert int(nonce2) >= int(nonce1)

    def test_get_headers_includes_api_key(self):
        # Given
        with patch('exchange_connector.kraken_utils.kraken_auth_utils.get_env_var') as mock_env:
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
        with patch('exchange_connector.kraken_utils.kraken_auth_utils.get_env_var') as mock_env:
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
