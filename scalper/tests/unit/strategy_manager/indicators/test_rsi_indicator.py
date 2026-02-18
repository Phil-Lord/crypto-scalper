import numpy as np
import pandas as pd
import pytest

from strategy_manager.indicators.rsi_indicator import RsiIndicator


@pytest.mark.strategy_manager
@pytest.mark.indicators
@pytest.mark.rsi_indicator
class TestRsiIndicator:
    @pytest.fixture
    def sample_prices(self) -> pd.DataFrame:
        np.random.seed(42)
        prices = np.random.uniform(100, 110, 200)
        return pd.DataFrame({'price': prices})

    def test_reset_clears_state(self):
        # Given
        indicator = RsiIndicator(window=14)
        prices = np.linspace(100, 120, 30)
        for price in prices:
            indicator.update(pd.Series({'price': price}))
        assert indicator.prev_price is not None
        assert indicator.avg_gain is not None

        # When
        indicator.reset()

        # Then
        assert indicator.prices == []
        assert indicator.avg_gain is None
        assert indicator.avg_loss is None
        assert indicator.prev_price is None

    def test_update_returns_none_initially(self):
        # Given
        indicator = RsiIndicator(window=14)
        prices = np.linspace(100, 105, 10)
        ohlc = pd.DataFrame({'price': prices})

        # When
        outputs = [indicator.update(row) for _, row in ohlc.iterrows()]

        # Then - Should return None for the first window+1 values
        assert all(v is None for v in outputs[:6])

    def test_vectorised_matches_update(self, sample_prices: pd.DataFrame):
        # Given
        window = 14
        indicator_update = RsiIndicator(window)
        indicator_vectorised = RsiIndicator(window)

        # When
        live_rsi = [indicator_update.update(row) for _, row in sample_prices.iterrows()]
        rsi_vect = indicator_vectorised.compute_vectorised(sample_prices)

        # Then
        for i in range(window + 200, len(sample_prices)):
            live_val = live_rsi[i]
            vect_val = rsi_vect.iloc[i]
            if pd.isna(live_val) or pd.isna(vect_val):
                assert pd.isna(live_val) and pd.isna(vect_val)
            else:
                assert abs(live_val - vect_val) < 1e-3, f'Mismatch at {i}: {live_val} != {vect_val}'

    def test_compute_vectorised_overbought_condition(self):
        # Given
        prices = np.linspace(100, 120, 30)
        ohlc = pd.DataFrame({'price': prices})

        # When
        rsi = RsiIndicator(window=14)
        result = rsi.compute_vectorised(ohlc)

        # Then
        assert result.iloc[-1] > 70, f'Expected RSI > 70 in uptrend, got {result.iloc[-1]}'

    def test_compute_vectorised_oversold_condition(self):
        # Given
        prices = np.linspace(120, 100, 30)
        ohlc = pd.DataFrame({'price': prices})

        # When
        rsi = RsiIndicator(window=14)
        result = rsi.compute_vectorised(ohlc)

        # Then
        assert result.iloc[-1] < 30, f'Expected RSI < 30 in downtrend, got {result.iloc[-1]}'

    def test_compute_vectorised_flat_market(self):
        # Given
        prices = [100.0] * 50
        ohlc = pd.DataFrame({'price': prices})

        # When
        rsi = RsiIndicator(window=14).compute_vectorised(ohlc)

        # Then - RSI of a flat price should be 100 (no losses, only gains)
        assert rsi.dropna().eq(100.0).all()

    def test_compute_vectorised_handles_nan(self):
        # Given
        prices = [100, 101, np.nan, 103, 104, 105, 106, 107, 108, 109, 110]
        ohlc = pd.DataFrame({'price': prices})
        window = 3

        # When
        rsi = RsiIndicator(window=window).compute_vectorised(ohlc)

        # Then
        assert pd.isna(rsi.iloc[2])
        assert not pd.isna(rsi.iloc[window + 3])
