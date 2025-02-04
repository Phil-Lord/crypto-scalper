import pandas as pd


def sma(prices: pd.Series, window: int) -> float:
    return prices.rolling(window=window).mean().iloc[-1]


def ema(prices: pd.Series, window: int) -> pd.Series:
    return prices.ewm(span=window, adjust=False).mean()


def rsi(prices: pd.Series, window: int) -> pd.Series:
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))
