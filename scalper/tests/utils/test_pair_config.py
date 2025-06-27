import pytest
from utils import get_kraken_pair, get_kraken_pair_symbols


def test_get_kraken_pair():
    assert get_kraken_pair('BTCGBP') == 'XXBTZGBP'
    with pytest.raises(ValueError):
        get_kraken_pair('INVALID')


def test_get_kraken_pair_symbols():
    symbols = get_kraken_pair_symbols('XXBTZGBP')
    assert symbols['base'] == 'XXBT'
    with pytest.raises(ValueError):
        get_kraken_pair_symbols('INVALID')
