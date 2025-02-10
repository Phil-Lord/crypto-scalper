def crossover(short_sma: float, long_sma: float, last_signal: str) -> tuple:
    if short_sma > long_sma and last_signal != 'buy':
        return 'buy', 'buy'
    elif short_sma < long_sma and last_signal == 'buy':
        return 'sell', 'sell'
    return 'hold', last_signal


def trending_crossover(prev_short_sma: float, prev_long_sma: float, short_sma: float, long_sma: float, last_signal: str):
    """ Determines buy/sell signals based on SMA crossover with trend confirmation. """
    if prev_short_sma <= prev_long_sma and short_sma > long_sma and last_signal != 'buy':
        return 'buy', 'buy'
    elif prev_short_sma >= prev_long_sma and short_sma < long_sma and last_signal == 'buy':
        return 'sell', 'sell'
    return 'hold', last_signal


def rsi_overbought_undersold(rsi: float, overbought: float, oversold: float) -> str:
    if rsi > overbought:
        return 'sell'
    elif rsi < oversold:
        return 'buy'
    return 'hold'
