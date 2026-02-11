import numpy as np
import pandas as pd
import pytest

from strategy_manager.indicators.sma_indicator import SmaIndicator


@pytest.mark.strategy_manager
@pytest.mark.indicators
@pytest.mark.sma_indicator
class TestSmaIndicator:
    @pytest.fixture
    def sample_prices(self) -> pd.DataFrame:
        np.random.seed(42)
        prices = np.random.uniform(90, 110, 100)
        return pd.DataFrame({'price': prices})

    def test_update_returns_none_initially(self):
        # Given
        indicator = SmaIndicator(window=5)
        ohlc = pd.Series({'price': 100.0})

        # When
        result = indicator.update(ohlc)

        # Then
        assert result is None

    def test_update_returns_value_after_window_filled(self):
        # Given
        indicator = SmaIndicator(window=3)
        prices = [100.0, 102.0, 104.0, 106.0]

        # When
        results = []
        for price in prices:
            results.append(indicator.update(pd.Series({'price': price})))

        # Then
        assert results[0] is None
        assert results[1] is None
        assert results[2] == pytest.approx(102.0)  # (100 + 102 + 104) / 3
        assert results[3] == pytest.approx(104.0)  # (102 + 104 + 106) / 3

    def test_vectorised_matches_update(self, sample_prices: pd.DataFrame):
        # Given
        window = 5
        indicator_update = SmaIndicator(window)
        indicator_vectorised = SmaIndicator(window)

        # When
        sma_live = [indicator_update.update(row) for _, row in sample_prices.iterrows()]
        sma_vect = indicator_vectorised.compute_vectorised(sample_prices)

        # Then
        for i in range(window, len(sample_prices)):
            live_val = sma_live[i]
            vect_val = sma_vect.iloc[i]
            assert abs(live_val - vect_val) < 1e-6, f'Mismatch at {i}: {live_val} != {vect_val}'

    def test_compute_vectorised_handles_nan_input(self):
        # Given
        prices = [100, 102, np.nan, 106, 108, 110]
        ohlc = pd.DataFrame({'price': prices})

        # When
        sma = SmaIndicator(window=3).compute_vectorised(ohlc)

        # Then
        # NaN input should lead to NaN output
        assert pd.isna(sma.iloc[2])
        # Subsequent valid inputs should still produce valid SMA values
        assert not pd.isna(sma.iloc[5])

    def test_compute_vectorised_constant_price_equals_price(self):
        # Given
        prices = [100] * 20
        ohlc = pd.DataFrame({'price': prices})

        # When
        sma = SmaIndicator(window=5).compute_vectorised(ohlc)

        # Then
        assert sma.dropna().eq(100).all()

    def test_compute_vectorised_increasing_prices_is_monotonic(self):
        # Given
        prices = list(range(1, 51))
        ohlc = pd.DataFrame({'price': prices})

        # When
        sma = SmaIndicator(window=5).compute_vectorised(ohlc)
        diff = sma.diff().dropna()

        # Then
        assert (diff >= 0).all()

    def test_compute_vectorised_short_window(self):
        # Given
        prices = [10, 20, 30]
        ohlc = pd.DataFrame({'price': prices})

        # When
        sma = SmaIndicator(window=3).compute_vectorised(ohlc)

        # Then
        expected = [np.nan, np.nan, 20.0]
        for i, val in enumerate(expected):
            if pd.isna(val):
                assert pd.isna(sma.iloc[i])
            else:
                assert sma.iloc[i] == val
