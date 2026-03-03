import numpy as np
import pandas as pd
import pytest

from strategy_manager.indicators.ema_indicator import EmaIndicator


@pytest.mark.strategy_manager
@pytest.mark.indicators
@pytest.mark.ema_indicator
class TestEmaIndicator:
    @pytest.fixture
    def sample_prices(self) -> pd.DataFrame:
        np.random.seed(0)
        prices = np.random.uniform(10, 20, 100)
        return pd.DataFrame({'close': prices})

    def test_update_returns_initial_value_on_first_call(self):
        # Given
        indicator = EmaIndicator(window=10)
        ohlc = pd.Series({'close': 100.0})

        # When
        result = indicator.update(ohlc)

        # Then
        assert result == 100.0

    def test_vectorised_matches_update(self, sample_prices: pd.DataFrame):
        # Given
        window = 10
        indicator_update = EmaIndicator(window)
        indicator_vectorised = EmaIndicator(window)

        # When
        ema_live = [indicator_update.update(row) for _, row in sample_prices.iterrows()]
        ema_vect = indicator_vectorised.compute_vectorised(sample_prices)

        # Then
        for i in range(len(sample_prices)):
            live_val = ema_live[i]
            vect_val = ema_vect.iloc[i]
            assert abs(live_val - vect_val) < 1e-6, f'Mismatch at {i}: {live_val} != {vect_val}'

    def test_compute_vectorised_flat_price(self):
        # Given
        ohlc = pd.DataFrame({'close': [100] * 50})

        # When
        ema = EmaIndicator(window=10).compute_vectorised(ohlc)

        # Then - EMA of a flat price should equal the price
        assert all(abs(val - 100) < 1e-8 for val in ema)

    def test_compute_vectorised_increasing_price(self):
        # Given
        prices = np.arange(1, 101)
        ohlc = pd.DataFrame({'close': prices})

        # When
        ema = EmaIndicator(window=10).compute_vectorised(ohlc)

        # Then - EMA should be monotonically increasing for increasing prices
        assert ema.is_monotonic_increasing

    def test_compute_vectorised_handles_nan_gracefully(self):
        # Given
        prices = [100, 101, np.nan, 103, 104]
        ohlc = pd.DataFrame({'close': prices})

        # When
        ema = EmaIndicator(window=3).compute_vectorised(ohlc)

        # Then
        assert not pd.isna(ema.iloc[2])
        assert pd.isna(ohlc['close'].iloc[2])
        assert not pd.isna(ema.iloc[4])

    def test_reset_clears_state(self):
        # Given
        indicator = EmaIndicator(window=5)
        for price in [100.0, 102.0, 104.0]:
            indicator.update(pd.Series({'close': price}))
        assert indicator.ema is not None

        # When
        indicator.reset()

        # Then
        assert indicator.ema is None
