import numpy as np
import pandas as pd
from strategy_manager.indicators import AdxIndicator


def test_vectorised_matches_update():
    np.random.seed(0)
    n = 1000
    ohlc = pd.DataFrame({
        'high': np.random.uniform(10, 20, n),
        'low': np.random.uniform(5, 10, n),
        'price': np.random.uniform(7, 18, n)
    })

    window = 3
    indicator = AdxIndicator(window)
    adx_live = [indicator.update(row) for _, row in ohlc.iterrows()]

    indicator_vect = AdxIndicator(window)
    adx_vect = indicator_vect.compute_vectorised(ohlc)

    for i in range(50, len(ohlc)):
        live_val = adx_live[i]
        vect_val = adx_vect.iloc[i]

        if pd.isna(live_val) or pd.isna(vect_val):
            assert pd.isna(live_val) and pd.isna(vect_val)
        else:
            assert abs(live_val - vect_val) < 1e-3, f"Mismatch at {i}: {live_val} != {vect_val}"
