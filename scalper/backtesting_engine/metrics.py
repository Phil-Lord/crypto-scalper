import numpy as np
import pandas as pd

# Crypto markets trade every calendar day, so daily-bar returns annualise over 365.
PERIODS_PER_YEAR = 365


def _periodic_returns(equity_curve: pd.Series) -> pd.Series:
    ''' Simple per-bar returns of an equity curve, with the leading NaN dropped. '''
    if len(equity_curve) < 2:
        raise ValueError('Need at least two points to compute returns.')
    return equity_curve.pct_change().dropna()


def sharpe_ratio(
    equity_curve: pd.Series, periods_per_year: int = PERIODS_PER_YEAR, risk_free: float = 0.0
) -> float:
    '''
    Annualised Sharpe ratio of an equity curve.

    Uses per-bar simple returns and population standard deviation (ddof=0), so it stays
    consistent with the downside deviation in `sortino_ratio` (both divide by N, counting
    flat/cash bars). Annualised by sqrt(periods_per_year).

    :param equity_curve: Portfolio value per bar, indexed by timestamp.
    :param periods_per_year: Bars per year for annualisation (default 365, daily crypto bars).
    :param risk_free: Per-bar risk-free return, subtracted from each bar's return (default 0).
    :return: Annualised Sharpe ratio, or 0.0 if returns have zero standard deviation.
    '''
    returns = _periodic_returns(equity_curve) - risk_free
    std = returns.std(ddof=0)
    if std == 0:
        return 0.0
    return float(returns.mean() / std * np.sqrt(periods_per_year))


def sortino_ratio(
    equity_curve: pd.Series, periods_per_year: int = PERIODS_PER_YEAR, target: float = 0.0
) -> float:
    '''
    Annualised Sortino ratio of an equity curve.

    Downside deviation is the root-mean-square of below-target returns, dividing by the
    *total* number of bars (flat/cash bars contribute a 0 return and are kept in N, not
    excluded) — the definition the swing experiment fixed before running. Annualised by
    sqrt(periods_per_year).

    :param equity_curve: Portfolio value per bar, indexed by timestamp.
    :param periods_per_year: Bars per year for annualisation (default 365, daily crypto bars).
    :param target: Minimum acceptable return (MAR) per bar (default 0).
    :return: Annualised Sortino ratio. Returns inf if there is no downside (and positive
        mean excess), or 0.0 if both downside and mean excess are zero.
    '''
    returns = _periodic_returns(equity_curve)
    excess = returns - target
    downside = np.minimum(excess, 0.0)
    downside_deviation = np.sqrt((downside ** 2).mean())
    if downside_deviation == 0:
        mean_excess = excess.mean()
        if mean_excess == 0:
            return 0.0
        return float('inf') if mean_excess > 0 else float('-inf')
    return float(excess.mean() / downside_deviation * np.sqrt(periods_per_year))
