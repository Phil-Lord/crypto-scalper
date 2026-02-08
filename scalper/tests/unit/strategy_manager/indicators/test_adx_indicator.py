import numpy as np
import pandas as pd
from strategy_manager.indicators.adx_indicator import AdxIndicator


def test_adx_update_returns_none_first():
    ohlc = pd.DataFrame({
        'high': [11, 12],
        'low': [9, 10],
        'price': [10, 11],
    })

    indicator = AdxIndicator(window=3)
    val0 = indicator.update(ohlc.iloc[0])
    val1 = indicator.update(ohlc.iloc[1])

    assert val0 is None
    assert isinstance(val1, float)


def test_adx_constant_prices():
    ohlc = pd.DataFrame({
        'high': [10] * 20,
        'low': [10] * 20,
        'price': [10] * 20,
    })

    indicator = AdxIndicator(window=5)
    adx_values = [indicator.update(row) for _, row in ohlc.iterrows()]

    for val in adx_values[1:]:
        assert val == 0 or pd.isna(val)


def test_adx_vectorised_length_and_type():
    ohlc = pd.DataFrame({
        'high': np.linspace(10, 20, 100),
        'low': np.linspace(9, 19, 100),
        'price': np.linspace(9.5, 19.5, 100),
    })

    indicator = AdxIndicator(window=14)
    adx_series = indicator.compute_vectorised(ohlc)

    assert isinstance(adx_series, pd.Series)
    assert len(adx_series) == len(ohlc)


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


def test_adx_increasing_trend_gives_high_adx():
    ohlc = pd.DataFrame({
        'high': np.arange(10, 30),
        'low': np.arange(9, 29),
        'price': np.arange(9.5, 29.5),
    })

    indicator = AdxIndicator(window=5)
    adx_series = indicator.compute_vectorised(ohlc)

    assert adx_series.iloc[-1] > 25  # ADX should be high in strong trend


def test_adx_no_trend_should_be_low():
    highs = [10, 12, 10, 12, 10, 12, 10, 12, 10, 12]
    lows = [9,  11, 9,  11, 9,  11, 9,  11, 9,  11]
    closes = [9.5, 11.5, 9.5, 11.5, 9.5, 11.5, 9.5, 11.5, 9.5, 11.5]

    ohlc = pd.DataFrame({'high': highs, 'low': lows, 'price': closes})

    indicator = AdxIndicator(window=3)
    adx_series = indicator.compute_vectorised(ohlc)

    assert adx_series.iloc[-1] < 25  # ADX should be low in choppy market
