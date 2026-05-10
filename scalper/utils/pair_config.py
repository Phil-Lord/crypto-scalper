from dataclasses import dataclass


@dataclass(frozen=True)
class PairSymbols:
    '''
    Dataclass representing the base and quote asset symbols for a trading pair.

    Attributes:
        base (str): Kraken base asset symbol, e.g. 'XXBT'.
        quote (str): Kraken quote asset symbol, e.g. 'ZGBP'.
    '''
    base: str
    quote: str


raw_to_kraken_pairs = {
    'BTCGBP': 'XXBTZGBP',
    'DOGEGBP': 'XXDGZGBP',
    'ETHGBP': 'XETHZGBP',
    'BTCUSD': 'XXBTZUSD'
}

kraken_pair_to_symbols = {
    'XXBTZGBP': PairSymbols(base='XXBT', quote='ZGBP'),
    'XXDGZGBP': PairSymbols(base='XXDG', quote='ZGBP'),
    'XETHZGBP': PairSymbols(base='XETH', quote='ZGBP'),
    'XXBTZUSD': PairSymbols(base='XXBT', quote='ZUSD')
}


def get_kraken_pair(raw_pair: str) -> str:
    ''' Given a raw pair (e.g. 'BTCGBP'), return the Kraken style pair (e.g. 'XXBTZGBP'). '''
    raw_pair = raw_pair.upper()
    kraken_pair = raw_to_kraken_pairs.get(raw_pair, None)
    if kraken_pair is None:
        raise ValueError(f'Invalid raw pair: {raw_pair}')
    return kraken_pair


_kraken_to_raw_pairs = {kraken: raw for raw, kraken in raw_to_kraken_pairs.items()}


def get_raw_pair(kraken_pair: str) -> str:
    ''' Given a Kraken pair (e.g. 'XXBTZGBP'), return the raw pair (e.g. 'BTCGBP'). '''
    raw_pair = _kraken_to_raw_pairs.get(kraken_pair, None)
    if raw_pair is None:
        raise ValueError(f'Invalid Kraken pair: {kraken_pair}')
    return raw_pair


def get_kraken_pair_symbols(kraken_pair: str) -> PairSymbols:
    ''' Given a Kraken pair (e.g. 'XXBTZGBP'), return the base and quote symbols. '''
    symbols = kraken_pair_to_symbols.get(kraken_pair, None)
    if symbols is None:
        raise ValueError(f'Invalid Kraken pair: {kraken_pair}')
    return symbols
