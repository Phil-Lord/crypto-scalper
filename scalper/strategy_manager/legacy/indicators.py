import numpy as np
import pandas as pd


def sma(prices: list[float], window: int) -> float:
    prices = pd.Series(prices)
    return prices.rolling(window=window).mean().iloc[-1]


def ema(prices: list[float], window: int) -> float:
    prices = pd.Series(prices)
    return prices.ewm(span=window, adjust=False).mean().iloc[-1]


def rsi(prices: list[float], window: float) -> float:
    prices = pd.Series(prices)
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean().iloc[-1]
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean().iloc[-1]
    rs = gain / loss if loss != 0 else float('inf')  # Avoid division by zero.
    return 100 - (100 / (1 + rs))


def adx(prices: list[float], window: int) -> dict:
    ''' Computes ADX along with +DI and -DI '''

    if len(prices) < window + 1:
        return {'adx': None, '+di': None, '-di': None}  # Not enough data yet

    df = pd.DataFrame({'close': prices})

    # Simulate Highs and Lows (Replace with real OHLC data if available)
    df['high'] = df['close'].rolling(2).max()
    df['low'] = df['close'].rolling(2).min()

    # Compute Directional Movement (+DM & -DM)
    df['+dm'] = np.where(df['high'].diff() > df['low'].diff(), df['high'].diff(), 0)
    df['-dm'] = np.where(df['low'].diff() > df['high'].diff(), df['low'].diff(), 0)

    # Compute True Range (TR)
    df['tr'] = np.maximum(df['high'] - df['low'],
                          np.maximum(abs(df['high'] - df['close'].shift(1)),
                                     abs(df['low'] - df['close'].shift(1))))

    # Wilder’s Smoothing (EMA-like calculation)
    df['smooth +dm'] = df['+dm'].rolling(window=window).mean()
    df['smooth -dm'] = df['-dm'].rolling(window=window).mean()
    df['smooth tr'] = df['tr'].rolling(window=window).mean()

    # Compute +DI and -DI
    df['+di'] = (df['smooth +dm'] / df['smooth tr']) * 100
    df['-di'] = (df['smooth -dm'] / df['smooth tr']) * 100

    # Compute DX (Directional Index)
    df['dx'] = (abs(df['+di'] - df['-di']) / (df['+di'] + df['-di'])) * 100

    # Compute ADX (Smoothed DX)
    df['adx'] = df['dx'].rolling(window=window).mean()

    return {
        'adx': df['adx'].iloc[-1],
        '+di': df['+di'].iloc[-1],
        '-di': df['-di'].iloc[-1]
    }
