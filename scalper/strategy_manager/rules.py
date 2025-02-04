def golden_cross(short_sma: float, long_sma: float, last_signal: str) -> tuple:
    if short_sma > long_sma and last_signal != 'buy':
        return 'buy', 'buy'
    elif short_sma < long_sma and last_signal == 'buy':
        return 'sell', 'sell'
    return 'hold', last_signal


def rsi_overbought_undersold(rsi: float, overbought=70, oversold=30) -> str:
    if rsi > overbought:
        return 'sell'
    elif rsi < oversold:
        return 'buy'
    return 'hold'
