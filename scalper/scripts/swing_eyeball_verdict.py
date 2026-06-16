'''
Issue #98 eyeball test: does a simple daily-bar trend follower show *visible*,
risk-adjusted downside protection across 2019-2026 — enough to justify #97?

Pre-registered pass threshold (decided before looking at any output):

    The strategy's full-span Sortino must CLEARLY EXCEED buy-and-hold's Sortino,
    and the profile must hold across ALL the param sets below — not one cherry-pick.
    Lower drawdown alone does NOT qualify (that is just reduced exposure, β<1).

Runs SmaStrategy (ma-crossover) at interval=1440 once over the full span per param
set, builds strategy + buy-and-hold equity curves on the same close-price basis,
reports full-span Sharpe/Sortino plus per-regime strategy/hold return ratios, and
plots the curves side by side. Eyeball the plot, read the verdict, stop either way.
'''
import logging
import sys

import click
import matplotlib.pyplot as plt
import pandas as pd

from backtesting_engine import (
    BacktestingEngine,
    buy_and_hold_equity_curve,
    buy_and_hold_ratio,
    sharpe_ratio,
    sortino_ratio,
    strategy_equity_curve,
)
from data_system import SQLAlchemyClient, SQLAlchemyTradeRepository
from strategy_manager import create_strategy
from utils import LOG_FORMAT, get_kraken_pair, load_env

load_env()
logging.basicConfig(level=logging.WARNING, format=LOG_FORMAT, stream=sys.stderr)

INITIAL_QUOTE_BALANCE = 1000.0
DAILY_INTERVAL = 1440

# Day-scale crossover pairs (short, long). Multiple sets guard against cherry-picking
# (issue #98 selection-bias guard): the profile must hold across all of them.
PARAM_SETS: list[tuple[int, int]] = [(20, 100), (50, 200), (50, 150), (100, 300)]

# Named calendar regimes spanned by the trade history (see issue #98).
REGIMES: list[tuple[str, str, str]] = [
    ('2019-20 accumulation', '2019-01-01', '2020-12-31'),
    ('2021 bull', '2021-01-01', '2021-12-31'),
    ('2022 bear', '2022-01-01', '2022-12-31'),
    ('2023 recovery', '2023-01-01', '2023-12-31'),
    ('2024 bull', '2024-01-01', '2024-12-31'),
    ('2025 flat', '2025-01-01', '2025-12-31'),
    ('2026 down', '2026-01-01', '2026-05-31'),
]


def max_drawdown(curve: pd.Series) -> float:
    ''' Largest peak-to-trough fractional decline of an equity curve (>= 0). '''
    running_peak = curve.cummax()
    return float((1 - curve / running_peak).max())


def window_ratio(curve: pd.Series, start: str, end: str) -> float | None:
    ''' First-to-last value ratio of the curve within [start, end], or None if empty. '''
    window = curve.loc[start:end]
    if window.empty:
        return None
    return float(window.iloc[-1] / window.iloc[0])


@click.command()
@click.option('--pair', '-p', default='BTCGBP', show_default=True, help='Trading pair.')
@click.option('--fee', '-f', default=0.0016, show_default=True, type=float,
              help='Per-side fee fraction (maker 0.0016, taker 0.004).')
@click.option('--no-plot', is_flag=True, help='Skip the equity-curve plot.')
def swing_eyeball_verdict(pair: str, fee: float, no_plot: bool) -> None:
    kraken_pair = get_kraken_pair(pair)
    repository = SQLAlchemyTradeRepository(SQLAlchemyClient())

    engine = BacktestingEngine(
        kraken_pair,
        create_strategy('SmaStrategy', {'short_window': 50, 'long_window': 200}),
        repository,
        interval=DAILY_INTERVAL,
        vectorised=True,
    )
    ohlc = engine.ohlc_window
    print(f'\nLoaded {len(ohlc)} daily bars '
          f'{ohlc.index.min().date()} -> {ohlc.index.max().date()} at fee {fee:.4f}\n')

    # Buy-and-hold is the single shared benchmark for every param set.
    hold_curve = buy_and_hold_equity_curve(ohlc, INITIAL_QUOTE_BALANCE, fee)
    hold_sortino = sortino_ratio(hold_curve)
    hold_sharpe = sharpe_ratio(hold_curve)
    hold_dd = max_drawdown(hold_curve)

    print('PRE-REGISTERED PASS THRESHOLD: strategy full-span Sortino must clearly exceed')
    print(f'buy-and-hold Sortino ({hold_sortino:.3f}) across ALL param sets. Lower drawdown')
    print('alone does NOT qualify.\n')
    print(f'Buy & hold: Sortino {hold_sortino:.3f} | Sharpe {hold_sharpe:.3f} '
          f'| maxDD {hold_dd:.1%} | final £{hold_curve.iloc[-1]:.0f}\n')

    strategy_curves: dict[str, pd.Series] = {}
    all_beat = True

    for short_window, long_window in PARAM_SETS:
        engine.strategy = create_strategy(
            'SmaStrategy', {'short_window': short_window, 'long_window': long_window}
        )
        engine.strategy.reset()
        engine.set_ohlc_window()
        results = engine.run()

        curve = strategy_equity_curve(results, INITIAL_QUOTE_BALANCE, fee)
        label = f'SMA {short_window}/{long_window}'
        strategy_curves[label] = curve

        strat_sortino = sortino_ratio(curve)
        strat_sharpe = sharpe_ratio(curve)
        beats = strat_sortino > hold_sortino
        all_beat = all_beat and beats
        n_trades = int(results['signal'].ne('hold').sum())

        print(f'{label:>12} | Sortino {strat_sortino:7.3f} ({"PASS" if beats else "FAIL"}) '
              f'| Sharpe {strat_sharpe:7.3f} | maxDD {max_drawdown(curve):5.1%} '
              f'| final £{curve.iloc[-1]:6.0f} | {n_trades} trades')

        # Per-regime relative performance: strategy ratio / buy-and-hold ratio.
        for name, start, end in REGIMES:
            strat_r = window_ratio(curve, start, end)
            hold_r = window_ratio(hold_curve, start, end)
            if strat_r is None or hold_r is None or hold_r == 0:
                continue
            rel = strat_r / hold_r
            print(f'{"":>14}{name:<22} strat {strat_r:5.2f}x  hold {hold_r:5.2f}x  '
                  f'rel {rel:5.2f}  {"+" if rel > 1 else ""}{(rel - 1) * 100:+.0f}pt')
        print()

    verdict = 'PASS' if all_beat else 'FAIL / INCONCLUSIVE'
    print(f'VERDICT: {verdict} — strategy Sortino beats buy-and-hold across all param sets: '
          f'{all_beat}')
    print('(Eyeball the plot too: a pass needs visible, risk-adjusted edge, not just luck.)\n')

    if not no_plot:
        _plot(strategy_curves, hold_curve, fee)


def _plot(strategy_curves: dict[str, pd.Series], hold_curve: pd.Series, fee: float) -> None:
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(hold_curve.index, hold_curve.values, label='Buy & hold', color='black',
            linewidth=2.0)
    for label, curve in strategy_curves.items():
        ax.plot(curve.index, curve.values, label=label, linewidth=1.2)
    for _, start, _ in REGIMES[1:]:
        ax.axvline(pd.Timestamp(start), color='grey', linestyle=':', linewidth=0.7)
    ax.set_yscale('log')
    ax.set_title(f'#98 daily-bar trend-follower vs buy & hold (XXBTZGBP, fee {fee:.4f})')
    ax.set_ylabel('Equity (£, log scale)')
    ax.legend(loc='upper left')
    ax.grid(True, which='both', alpha=0.3)
    fig.tight_layout()
    plt.show()


if __name__ == '__main__':
    swing_eyeball_verdict()
