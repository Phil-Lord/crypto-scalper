import pandas as pd
import pytest

from strategy_manager.indicators.atr_indicator import AtrIndicator


def test_atr_update_returns_none_initially():
    indicator = AtrIndicator(window=3)
    ohlc = pd.Series({'high': 105, 'low': 95, 'price': 100})
    result = indicator.update(ohlc)
    assert result is None


def test_atr_update_returns_ratio():
    indicator = AtrIndicator(window=3)

    # First call initialises state
    indicator.update(pd.Series({'high': 105, 'low': 95, 'price': 100}))

    # Next input
    ohlc = pd.Series({'high': 110, 'low': 90, 'price': 102})
    result = indicator.update(ohlc)

    assert result is not None
    assert isinstance(result, float)
    assert result == pytest.approx(0.19607843137254902, rel=1e-3)


def test_atr_vectorised_matches_manual_values():
    indicator = AtrIndicator(window=3)

    df = pd.DataFrame({
        'high': [105, 110, 115, 120],
        'low':  [95, 90,  100, 110],
        'price': [100, 102, 107, 115]
    }, index=pd.date_range("2024-01-01", periods=4, freq="min"))

    result = indicator.compute_vectorised(df)

    assert isinstance(result, pd.Series)
    assert result.name == 'atr'
    assert result.shape[0] == df.shape[0]
    assert result.notna().sum() > 0
    assert (result > 0).all()
    assert (result < 1).all()
    assert result.iloc[-1] == pytest.approx(0.1181964573268921, rel=1e-3)
