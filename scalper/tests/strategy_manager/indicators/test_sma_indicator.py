import pandas as pd
import numpy as np
from strategy_manager.indicators import SmaIndicator


def test_sma_vectorised_matches_update():
    np.random.seed(42)
    prices = np.random.uniform(90, 110, 100)
    ohlc = pd.DataFrame({'price': prices})
    window = 5

    indicator = SmaIndicator(window)
    sma_live = [indicator.update(row) for _, row in ohlc.iterrows()]
    sma_vect = SmaIndicator(window).compute_vectorised(ohlc)

    for i in range(window, len(prices)):
        live_val = sma_live[i]
        vect_val = sma_vect.iloc[i]
        assert abs(live_val - vect_val) < 1e-6, f"Mismatch at {i}: {live_val} != {vect_val}"


def test_sma_handles_nan_input():
    prices = [100, 102, np.nan, 106, 108, 110]
    ohlc = pd.DataFrame({'price': prices})
    sma = SmaIndicator(window=3).compute_vectorised(ohlc)

    assert pd.isna(sma.iloc[2]), "SMA should be NaN where there is insufficient data"
    assert not pd.isna(sma.iloc[5]), "SMA should compute if enough valid data is present"


def test_sma_constant_price_equals_price():
    prices = [100] * 20
    ohlc = pd.DataFrame({'price': prices})
    sma = SmaIndicator(window=5).compute_vectorised(ohlc)

    assert sma.dropna().eq(100).all(), "SMA should equal constant price when input is constant"


def test_sma_increasing_prices_is_monotonic():
    prices = list(range(1, 51))
    ohlc = pd.DataFrame({'price': prices})
    sma = SmaIndicator(window=5).compute_vectorised(ohlc)

    # After enough data, SMA should be strictly increasing
    diff = sma.diff().dropna()
    assert (diff >= 0).all(), "SMA should be monotonically increasing on increasing prices"


def test_sma_short_window_returns_first_prices():
    prices = [10, 20, 30]
    ohlc = pd.DataFrame({'price': prices})
    sma = SmaIndicator(window=3).compute_vectorised(ohlc)

    expected = [np.nan, np.nan, 20.0]
    for i, val in enumerate(expected):
        if pd.isna(val):
            assert pd.isna(sma.iloc[i])
        else:
            assert sma.iloc[i] == val
