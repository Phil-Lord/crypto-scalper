import numpy as np
import pandas as pd
import pytest

from strategy_manager.indicators.adx_indicator import AdxIndicator


@pytest.mark.strategy_manager
@pytest.mark.indicators
@pytest.mark.adx_indicator
class TestAdxIndicator:
    @pytest.fixture
    def sample_ohlc(self) -> pd.DataFrame:
        np.random.seed(0)
        n = 1000
        return pd.DataFrame({
            'high': np.random.uniform(10, 20, n),
            'low': np.random.uniform(5, 10, n),
            'close': np.random.uniform(7, 18, n)
        })

    def test_reset_clears_state(self):
        # Given
        indicator = AdxIndicator(window=3)
        ohlc = pd.DataFrame({
            'high': [11, 12, 13, 14],
            'low': [9, 10, 11, 12],
            'close': [10, 11, 12, 13],
        })
        for _, row in ohlc.iterrows():
            indicator.update(row)
        assert indicator.adx is not None

        # When
        indicator.reset()

        # Then
        assert indicator.prev_high is None
        assert indicator.prev_low is None
        assert indicator.prev_close is None
        assert indicator.smoothed_tr is None
        assert indicator.smoothed_plus_dm is None
        assert indicator.smoothed_minus_dm is None
        assert indicator.adx is None

    def test_update_returns_none_first(self):
        # Given
        ohlc = pd.DataFrame({
            'high': [11, 12],
            'low': [9, 10],
            'close': [10, 11],
        })
        indicator = AdxIndicator(window=3)

        # When
        val0 = indicator.update(ohlc.iloc[0])
        val1 = indicator.update(ohlc.iloc[1])

        # Then
        assert val0 is None
        assert isinstance(val1, float)

    def test_update_constant_prices(self):
        # Given
        ohlc = pd.DataFrame({
            'high': [10] * 20,
            'low': [10] * 20,
            'close': [10] * 20,
        })
        indicator = AdxIndicator(window=5)

        # When
        adx_values = [indicator.update(row) for _, row in ohlc.iterrows()]

        # Then
        for val in adx_values[1:]:
            assert val == 0 or pd.isna(val)

    def test_compute_vectorised_length_and_type(self):
        # Given
        ohlc = pd.DataFrame({
            'high': np.linspace(10, 20, 100),
            'low': np.linspace(9, 19, 100),
            'close': np.linspace(9.5, 19.5, 100),
        })

        # When
        indicator = AdxIndicator(window=14)
        adx_series = indicator.compute_vectorised(ohlc)

        # Then
        assert isinstance(adx_series, pd.Series)
        assert len(adx_series) == len(ohlc)

    def test_vectorised_matches_update(self, sample_ohlc: pd.DataFrame):
        # Given
        window = 3
        indicator_update = AdxIndicator(window)
        indicator_vectorised = AdxIndicator(window)

        # When
        adx_live = [indicator_update.update(row) for _, row in sample_ohlc.iterrows()]
        adx_vect = indicator_vectorised.compute_vectorised(sample_ohlc)

        # Then
        for i in range(50, len(sample_ohlc)):
            live_val = adx_live[i]
            vect_val = adx_vect.iloc[i]

            if pd.isna(live_val) or pd.isna(vect_val):
                assert pd.isna(live_val) and pd.isna(vect_val)
            else:
                assert abs(live_val - vect_val) < 1e-3, f'Mismatch at {i}: {live_val} != {vect_val}'

    def test_compute_vectorised_increasing_trend_gives_high_adx(self):
        # Given
        ohlc = pd.DataFrame({
            'high': np.arange(10, 30),
            'low': np.arange(9, 29),
            'close': np.arange(9.5, 29.5),
        })

        # When
        indicator = AdxIndicator(window=5)
        adx_series = indicator.compute_vectorised(ohlc)

        # Then
        assert adx_series.iloc[-1] > 25

    def test_compute_vectorised_no_trend_low_adx(self):
        # Given
        highs = [10, 12, 10, 12, 10, 12, 10, 12, 10, 12]
        lows = [9,  11, 9,  11, 9,  11, 9,  11, 9,  11]
        closes = [9.5, 11.5, 9.5, 11.5, 9.5, 11.5, 9.5, 11.5, 9.5, 11.5]
        ohlc = pd.DataFrame({'high': highs, 'low': lows, 'close': closes})

        # When
        indicator = AdxIndicator(window=3)
        adx_series = indicator.compute_vectorised(ohlc)

        # Then - ADX should be low due to lack of clear trend
        assert adx_series.iloc[-1] < 25
