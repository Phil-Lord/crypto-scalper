import pytest

from utils.pair_config import get_kraken_pair, get_kraken_pair_symbols, PairSymbols


@pytest.mark.utils
@pytest.mark.pair_config
class TestGetKrakenPair:
    def test_returns_kraken_pair_for_valid_input(self):
        # When
        result = get_kraken_pair('BTCGBP')

        # Then
        assert result == 'XXBTZGBP'

    def test_handles_lowercase_input(self):
        # When
        result = get_kraken_pair('btcgbp')

        # Then
        assert result == 'XXBTZGBP'

    def test_raises_value_error_for_invalid_pair(self):
        # When / Then
        with pytest.raises(ValueError):
            get_kraken_pair('INVALID')


@pytest.mark.utils
@pytest.mark.pair_config
class TestGetKrakenPairSymbols:
    def test_returns_base_and_quote_symbols(self):
        # When
        symbols = get_kraken_pair_symbols('XXBTZGBP')

        # Then
        assert isinstance(symbols, PairSymbols)
        assert symbols.base == 'XXBT'
        assert symbols.quote == 'ZGBP'

    def test_raises_value_error_for_invalid_pair(self):
        # When / Then
        with pytest.raises(ValueError):
            get_kraken_pair_symbols('INVALID')
