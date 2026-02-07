import numpy as np
import pandas as pd

from strategy_manager.indicators import RsiIndicator


def test_rsi_vectorised_matches_update():
    np.random.seed(42)
    prices = np.random.uniform(100, 110, 200)
    ohlc = pd.DataFrame({'price': prices})

    window = 14
    rsi = RsiIndicator(window)
    live_rsi = [rsi.update(row) for _, row in ohlc.iterrows()]

    rsi_vect = RsiIndicator(window).compute_vectorised(ohlc)

    for i in range(window + 200, len(ohlc)):
        live_val = live_rsi[i]
        vect_val = rsi_vect.iloc[i]
        if pd.isna(live_val) or pd.isna(vect_val):
            assert pd.isna(live_val) and pd.isna(vect_val)
        else:
            assert abs(live_val - vect_val) < 1e-3, f"Mismatch at {i}: {live_val} != {vect_val}"


def test_rsi_returns_none_for_initial_values():
    prices = np.linspace(100, 105, 10)
    ohlc = pd.DataFrame({'price': prices})
    rsi = RsiIndicator(window=5)
    outputs = [rsi.update(row) for _, row in ohlc.iterrows()]

    # Should return None for the first window+1 values
    assert all(v is None for v in outputs[:6]), "RSI should return None until enough data"


def test_rsi_overbought_condition():
    prices = np.linspace(100, 120, 30)
    ohlc = pd.DataFrame({'price': prices})
    rsi = RsiIndicator(window=14)
    result = rsi.compute_vectorised(ohlc)
    assert result.iloc[-1] > 70, f"Expected RSI > 70 in uptrend, got {result.iloc[-1]}"


def test_rsi_oversold_condition():
    prices = np.linspace(120, 100, 30)
    ohlc = pd.DataFrame({'price': prices})
    rsi = RsiIndicator(window=14)
    result = rsi.compute_vectorised(ohlc)
    assert result.iloc[-1] < 30, f"Expected RSI < 30 in downtrend, got {result.iloc[-1]}"


def test_rsi_flat_market_should_return_100():
    prices = [100.0] * 50
    ohlc = pd.DataFrame({'price': prices})
    rsi = RsiIndicator(window=14).compute_vectorised(ohlc)

    # Expect RSI = 100 for all post-initial rows
    assert rsi.dropna().eq(100.0).all(), "RSI should be 100 in a perfectly flat market"


def test_rsi_nan_handling():
    prices = [100, 101, np.nan, 103, 104, 105, 106, 107, 108, 109, 110]
    ohlc = pd.DataFrame({'price': prices})
    window = 3
    rsi = RsiIndicator(window=window).compute_vectorised(ohlc)

    # Ensure NaNs are preserved in RSI output
    assert pd.isna(rsi.iloc[2]), "RSI should be NaN where price is NaN"

    # Ensure RSI resumes calculation after NaNs
    assert not pd.isna(rsi.iloc[window + 3]), "RSI should compute after enough valid data post-NaN"
