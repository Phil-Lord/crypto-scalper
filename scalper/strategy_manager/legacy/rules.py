def crossover(short_sma: float, long_sma: float, last_signal: str) -> tuple:
    if short_sma > long_sma and last_signal != 'buy':
        return 'buy', 'buy'
    elif short_sma < long_sma and last_signal == 'buy':
        return 'sell', 'sell'
    return 'hold', last_signal


def trending_crossover(short_sma: float, long_sma: float, last_signal: str, counter: int, threshold: int):
    """ Determines buy/sell signals based on SMA crossover with trend confirmation. """
    if short_sma > long_sma:
        counter += 1
        if counter >= threshold and last_signal != 'buy':
            return 'buy', 'buy', counter
    elif short_sma < long_sma:
        counter += 1
        if counter >= threshold and last_signal == 'buy':
            return 'sell', 'sell', counter
    else:
        counter = 0
    return 'hold', last_signal, counter


def rsi_overbought_undersold(rsi: float, overbought: float, oversold: float) -> str:
    if rsi > overbought:
        return 'sell'
    elif rsi < oversold:
        return 'buy'
    return 'hold'


def get_adx_signal(adx, plus_di, minus_di):
    if adx is not None and adx > 20:  # Only trade in strong trends
        if plus_di > minus_di:
            signal = 'buy'
        elif minus_di > plus_di:
            signal = 'sell'
        else:
            signal = 'hold'
    else:
        signal = 'hold'
    return signal
