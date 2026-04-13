import pytest
from unittest.mock import patch

from exchange_connector.kraken_utils.kraken_auth_utils import get_nonce, get_headers, get_signature


@pytest.mark.exchange_connector
@pytest.mark.kraken_utils
@pytest.mark.kraken_auth_utils
class TestKrakenAuthUtils:
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

    def test_get_nonce_is_increasing(self):
        # When
        nonce1 = get_nonce()
        nonce2 = get_nonce()

        # Then
        assert int(nonce2) >= int(nonce1)

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


@pytest.mark.exchange_connector
@pytest.mark.kraken_utils
@pytest.mark.kraken_auth_utils
class TestGetSignature:
    def test_signature_is_identical_for_str_enum_and_plain_str(self):
        '''
        Verify that params containing str-based Enum values produce the same
        signature as params with plain string values. This prevents HMAC
        mismatches when requests.post encodes the body with the enum's str
        value while the signature is computed over the repr.
        '''
        from enum import Enum

        class Signal(str, Enum):
            BUY = 'buy'

        private_key = 'dGVzdF9wcml2YXRlX2tleQ=='
        nonce = '123456789'
        endpoint = '/0/private/AddOrder'

        params_with_enum = {
            'nonce': nonce,
            'ordertype': 'market',
            'type': Signal.BUY,
            'pair': 'XXBTZGBP',
            'volume': '0.001',
        }

        params_with_str = {
            'nonce': nonce,
            'ordertype': 'market',
            'type': 'buy',
            'pair': 'XXBTZGBP',
            'volume': '0.001',
        }

        sig_enum = get_signature(private_key, params_with_enum, nonce, endpoint)
        sig_str = get_signature(private_key, params_with_str, nonce, endpoint)

        assert sig_enum == sig_str
        assert isinstance(sig_enum, str)
