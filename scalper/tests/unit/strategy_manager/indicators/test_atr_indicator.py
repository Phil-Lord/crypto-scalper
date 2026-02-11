import numpy as np
import pandas as pd
import pytest

from strategy_manager.indicators.atr_indicator import AtrIndicator


@pytest.mark.strategy_manager
@pytest.mark.indicators
@pytest.mark.atr_indicator
class TestAtrIndicator:
    @pytest.fixture
    def sample_ohlc(self) -> pd.DataFrame:
        '''Random OHLC data for testing.'''
        np.random.seed(42)
        n = 100
        return pd.DataFrame({
            'high': np.random.uniform(100, 110, n),
            'low':  np.random.uniform(90, 100, n),
            'price': np.random.uniform(95, 105, n)
        })

    def test_update_returns_none_initially(self):
        # Given
        indicator = AtrIndicator(window=3)
        ohlc = pd.Series({'high': 105, 'low': 95, 'price': 100})

        # When
        result = indicator.update(ohlc)

        # Then
        assert result is None

    def test_update_returns_ratio_after_initialization(self):
        # Given
        indicator = AtrIndicator(window=3)
        indicator.update(pd.Series({'high': 105, 'low': 95, 'price': 100}))

        # When
        ohlc = pd.Series({'high': 110, 'low': 90, 'price': 102})
        result = indicator.update(ohlc)

        # Then
        assert result is not None
        assert isinstance(result, float)
        assert result == pytest.approx(0.19607843137254902, rel=1e-3)

    def test_compute_vectorised_output_format(self):
        # Given
        indicator = AtrIndicator(window=3)
        df = pd.DataFrame({
            'high': [105, 110, 115, 120],
            'low':  [95, 90,  100, 110],
            'price': [100, 102, 107, 115]
        }, index=pd.date_range('2024-01-01', periods=4, freq='min'))

        # When
        result = indicator.compute_vectorised(df)

        # Then
        assert isinstance(result, pd.Series)
        assert result.name == 'atr'
        assert result.shape[0] == df.shape[0]
        assert result.notna().sum() > 0
        assert (result > 0).all()
        assert (result < 1).all()
        assert result.iloc[-1] == pytest.approx(0.1181964573268921, rel=1e-3)

    def test_vectorised_matches_update(self, sample_ohlc: pd.DataFrame):
        # Given
        window = 14
        indicator_update = AtrIndicator(window)
        indicator_vectorised = AtrIndicator(window)

        # When
        live_atr = [indicator_update.update(row) for _, row in sample_ohlc.iterrows()]
        atr_vect = indicator_vectorised.compute_vectorised(sample_ohlc)

        # Then - Start comparing after warm-up period (EWM needs time to stabilize)
        for i in range(30, len(sample_ohlc)):
            live_val = live_atr[i]
            vect_val = atr_vect.iloc[i]
            if pd.isna(live_val) or pd.isna(vect_val):
                assert pd.isna(live_val) and pd.isna(vect_val)
            else:
                assert abs(live_val - vect_val) < 1e-3, f'Mismatch at {i}: {live_val} != {vect_val}'
