import pandas as pd


def sma(prices: list[float], window: int) -> float:
    prices = pd.Series(prices)
    return prices.rolling(window=window).mean().iloc[-1]


def ema(prices: list[float], window: int) -> float:
    prices = pd.Series(prices)
    return prices.ewm(span=window, adjust=False).mean().iloc[-1]


def rsi(prices: float, window: int) -> pd.Series:
    prices = pd.Series(prices)
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))
