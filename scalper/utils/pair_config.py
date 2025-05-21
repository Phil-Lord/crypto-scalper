raw_to_kraken_pairs = {
    'BTCGBP': 'XXBTZGBP',
    'DOGEGBP': 'XXDGZGBP',
    'ETHGBP': 'XETHZGBP'
}


def get_kraken_pair(raw_pair: str) -> str:
    ''' Given a raw pair (e.g. 'BTCGBP'), return the Kraken style pair (e.g. 'XXBTZGBP'). '''
    raw_pair = raw_pair.upper()
    # TODO: If not in raw_to_kraken_pairs, hit tradable pairs endpoint.
    return raw_to_kraken_pairs.get(raw_pair, None)
