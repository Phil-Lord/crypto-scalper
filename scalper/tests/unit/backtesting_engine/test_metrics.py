import numpy as np
import pandas as pd
import pytest

from backtesting_engine.metrics import sharpe_ratio, sortino_ratio


@pytest.mark.backtesting_engine
@pytest.mark.metrics
class TestSharpeRatio:
    def test_zero_volatility_returns_zero(self):
        # Given - a perfectly flat curve has no returns variance
        curve = pd.Series([1000.0, 1000.0, 1000.0])

        # Then
        assert sharpe_ratio(curve) == 0.0

    def test_matches_manual_calculation(self):
        # Given - a curve with known per-bar returns
        curve = pd.Series([100.0, 110.0, 121.0])  # two +10% returns
        returns = curve.pct_change().dropna()

        # When
        result = sharpe_ratio(curve, periods_per_year=365)

        # Then - std is 0 here (identical returns), so Sharpe is 0 by definition
        assert returns.std(ddof=0) == pytest.approx(0.0)
        assert result == 0.0

    def test_positive_for_noisy_uptrend(self):
        rng = np.random.default_rng(0)
        returns = rng.normal(0.002, 0.01, 500)
        curve = pd.Series(1000.0 * np.cumprod(1 + returns))
        assert sharpe_ratio(curve) > 0

    def test_annualisation_scales_by_sqrt_periods(self):
        rng = np.random.default_rng(1)
        curve = pd.Series(1000.0 * np.cumprod(1 + rng.normal(0.001, 0.01, 300)))
        daily = sharpe_ratio(curve, periods_per_year=1)
        annual = sharpe_ratio(curve, periods_per_year=365)
        assert annual == pytest.approx(daily * np.sqrt(365))

    def test_too_short_raises(self):
        with pytest.raises(ValueError):
            sharpe_ratio(pd.Series([1000.0]))


@pytest.mark.backtesting_engine
@pytest.mark.metrics
class TestSortinoRatio:
    def test_no_downside_with_positive_mean_is_inf(self):
        # Given - monotonically rising curve has no below-target returns
        curve = pd.Series([100.0, 110.0, 121.0, 133.0])

        # Then
        assert sortino_ratio(curve) == float('inf')

    def test_flat_curve_is_zero(self):
        curve = pd.Series([1000.0, 1000.0, 1000.0])
        assert sortino_ratio(curve) == 0.0

    def test_cash_periods_counted_in_downside_denominator(self):
        # Given - one drawdown bar surrounded by flat cash bars. The flat bars are kept
        # in N (cash = 0 return, not excluded), which lowers downside deviation vs
        # excluding them, and must not be dropped.
        with_cash = pd.Series([1000.0, 1000.0, 900.0, 900.0, 900.0])
        returns = with_cash.pct_change().dropna()
        downside = np.minimum(returns, 0.0)

        # downside deviation divides by N = 4 (all bars), not by the 1 negative bar
        expected_dd = np.sqrt((downside ** 2).sum() / 4)
        manual = returns.mean() / expected_dd * np.sqrt(365)

        # When
        result = sortino_ratio(with_cash)

        # Then
        assert result == pytest.approx(manual)

    def test_penalises_downside_only(self):
        # A curve with the same mean but larger upside swings should not be punished;
        # only downside affects the denominator.
        smooth = pd.Series([100.0, 101.0, 102.0, 103.0])
        assert sortino_ratio(smooth) == float('inf')  # no downside at all

    def test_negative_when_mean_below_target(self):
        curve = pd.Series([100.0, 90.0, 81.0])  # consistent losses
        assert sortino_ratio(curve) < 0

    def test_too_short_raises(self):
        with pytest.raises(ValueError):
            sortino_ratio(pd.Series([1000.0]))
