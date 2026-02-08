import numpy as np
import pandas as pd

from strategy_manager.indicators.ema_indicator import EmaIndicator


def test_vectorised_matches_update():
    np.random.seed(0)
    prices = np.random.uniform(10, 20, 100)
    ohlc = pd.DataFrame({'price': prices})

    window = 10
    indicator = EmaIndicator(window)
    ema_live = [indicator.update(row) for _, row in ohlc.iterrows()]

    indicator_vect = EmaIndicator(window)
    ema_vect = indicator_vect.compute_vectorised(ohlc)

    for i in range(len(ohlc)):
        live_val = ema_live[i]
        vect_val = ema_vect.iloc[i]
        assert abs(live_val - vect_val) < 1e-6, f"Mismatch at {i}: {live_val} != {vect_val}"


def test_ema_flat_price():
    ohlc = pd.DataFrame({'price': [100] * 50})
    ema = EmaIndicator(window=10).compute_vectorised(ohlc)

    assert all(abs(val - 100) < 1e-8 for val in ema), "EMA should be flat at 100 for constant price"


def test_ema_increasing_price():
    prices = np.arange(1, 101)
    ohlc = pd.DataFrame({'price': prices})
    ema = EmaIndicator(window=10).compute_vectorised(ohlc)

    # EMA should also be strictly increasing
    assert ema.is_monotonic_increasing, "EMA should increase with increasing prices"


def test_ema_handles_nan_gracefully():
    prices = [100, 101, np.nan, 103, 104]
    ohlc = pd.DataFrame({'price': prices})
    ema = EmaIndicator(window=3).compute_vectorised(ohlc)

    # Check that NaNs are skipped, not propagated
    assert not pd.isna(ema.iloc[2]), "EMA should not be NaN; ewm skips NaNs by default"
    assert pd.isna(ohlc['price'].iloc[2]), "Original price at index 2 should still be NaN"
    assert not pd.isna(ema.iloc[4]), "EMA should continue even after a NaN input"
