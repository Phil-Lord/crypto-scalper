raw_to_kraken_pairs = {
    'BTCGBP': 'XXBTZGBP',
    'DOGEGBP': 'XXDGZGBP',
    'ETHGBP': 'XETHZGBP',
    'BTCUSD': 'XXBTZUSD'
}

kraken_pair_to_symbols = {
    'XXBTZGBP': {'base': 'XXBT', 'quote': 'ZGBP'},
    'XXDGZGBP': {'base': 'XXDG', 'quote': 'ZGBP'},
    'XETHZGBP': {'base': 'XETH', 'quote': 'ZGBP'},
    'XXBTZUSD': {'base': 'XXBT', 'quote': 'ZUSD'}
}


def get_kraken_pair(raw_pair: str) -> str:
    ''' Given a raw pair (e.g. 'BTCGBP'), return the Kraken style pair (e.g. 'XXBTZGBP'). '''
    raw_pair = raw_pair.upper()
    kraken_pair = raw_to_kraken_pairs.get(raw_pair, None)
    if kraken_pair is None:
        raise ValueError(f"Invalid raw pair: {raw_pair}")
    return kraken_pair


def get_kraken_pair_symbols(kraken_pair: str) -> dict:
    ''' Given a Kraken pair (e.g. 'XXBTZGBP'), return the base and quote symbols. '''
    symbols = kraken_pair_to_symbols.get(kraken_pair, None)
    if symbols is None:
        raise ValueError(f"Invalid Kraken pair: {kraken_pair}")
    return symbols
