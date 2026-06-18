import pandas as pd
import pytest

from backtesting_engine.benchmark import buy_and_hold_equity_curve, buy_and_hold_ratio


@pytest.mark.backtesting_engine
@pytest.mark.benchmark
class TestBuyAndHoldRatio:
    @pytest.fixture
    def rising_window(self) -> pd.DataFrame:
        '''OHLC window where close doubles from first to last bar.'''
        index = pd.date_range('2024-01-01', periods=3, freq='D')
        return pd.DataFrame({'close': [100.0, 150.0, 200.0]}, index=index)

    def test_uses_first_and_last_close_with_fees_both_sides(self, rising_window):
        # When
        ratio = buy_and_hold_ratio(rising_window, fee=0.004)

        # Then - 200/100 net of the fee on entry and exit
        assert ratio == pytest.approx(2.0 * (1 - 0.004) ** 2)

    def test_default_fee_is_taker(self, rising_window):
        assert buy_and_hold_ratio(rising_window) == pytest.approx(
            buy_and_hold_ratio(rising_window, fee=0.004)
        )

    def test_maker_fee_beats_taker(self, rising_window):
        assert buy_and_hold_ratio(rising_window, fee=0.0016) > buy_and_hold_ratio(
            rising_window, fee=0.004
        )

    def test_zero_fee_is_pure_price_ratio(self, rising_window):
        assert buy_and_hold_ratio(rising_window, fee=0.0) == pytest.approx(2.0)

    def test_ignores_intermediate_prices(self):
        # Given - a spike in the middle must not affect a first-to-last ratio
        index = pd.date_range('2024-01-01', periods=3, freq='D')
        window = pd.DataFrame({'close': [100.0, 999.0, 100.0]}, index=index)

        # Then
        assert buy_and_hold_ratio(window, fee=0.0) == pytest.approx(1.0)

    def test_single_bar_is_round_trip_fee_only(self):
        # Given - first close equals last close
        window = pd.DataFrame({'close': [100.0]}, index=[pd.Timestamp('2024-01-01')])

        # Then
        assert buy_and_hold_ratio(window, fee=0.004) == pytest.approx((1 - 0.004) ** 2)

    def test_empty_window_raises(self):
        with pytest.raises(ValueError):
            buy_and_hold_ratio(pd.DataFrame({'close': []}))


@pytest.mark.backtesting_engine
@pytest.mark.benchmark
class TestBuyAndHoldEquityCurve:
    @pytest.fixture
    def rising_window(self) -> pd.DataFrame:
        index = pd.date_range('2024-01-01', periods=3, freq='D')
        return pd.DataFrame({'close': [100.0, 150.0, 200.0]}, index=index)

    def test_aligned_to_window_index(self, rising_window):
        curve = buy_and_hold_equity_curve(rising_window)
        assert list(curve.index) == list(rising_window.index)

    def test_final_value_equals_ratio_times_initial(self, rising_window):
        # The curve endpoint must reconcile with the scalar ratio for the same fee.
        initial = 1000.0
        curve = buy_and_hold_equity_curve(rising_window, initial, fee=0.004)
        expected = initial * buy_and_hold_ratio(rising_window, fee=0.004)
        assert curve.iloc[-1] == pytest.approx(expected)

    def test_returns_track_price_changes_independent_of_fee(self, rising_window):
        # Bar-to-bar returns are the same as raw price returns; fee scaling cancels.
        taker = buy_and_hold_equity_curve(rising_window, fee=0.004).pct_change().dropna()
        maker = buy_and_hold_equity_curve(rising_window, fee=0.0016).pct_change().dropna()
        price_returns = rising_window['close'].pct_change().dropna()
        pd.testing.assert_series_equal(taker, maker, check_names=False)
        pd.testing.assert_series_equal(taker, price_returns, check_names=False)

    def test_scales_with_initial_balance(self, rising_window):
        small = buy_and_hold_equity_curve(rising_window, 1000.0)
        large = buy_and_hold_equity_curve(rising_window, 5000.0)
        pd.testing.assert_series_equal(large, small * 5, check_names=False)

    def test_empty_window_raises(self):
        with pytest.raises(ValueError):
            buy_and_hold_equity_curve(pd.DataFrame({'close': []}))
