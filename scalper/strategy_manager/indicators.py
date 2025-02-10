import pandas as pd


def sma(prices: list[float], window: int) -> float:
    prices = pd.Series(prices)
    return prices.rolling(window=window).mean().iloc[-1]


def sma_trend(prices: list[float], window: int) -> tuple:
    prices = pd.Series(prices)
    sma = prices.rolling(window=window).mean()
    return sma.iloc[-2], sma.iloc[-1]


def ema(prices: list[float], window: int) -> float:
    prices = pd.Series(prices)
    return prices.ewm(span=window, adjust=False).mean().iloc[-1]


def ema_trend(prices: list[float], window: int) -> tuple:
    prices = pd.Series(prices)
    ema = prices.ewm(span=window, adjust=False).mean()
    return ema.iloc[-2], ema.iloc[-1]


def rsi(prices: list[float], window: float) -> float:
    prices = pd.Series(prices)
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean().iloc[-1]
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean().iloc[-1]
    rs = gain / loss if loss != 0 else float('inf')  # Avoid division by zero.
    return 100 - (100 / (1 + rs))
