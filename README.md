# Crypto Scalper

A crypto trading bot for Kraken. Indicator-based strategies are tuned by [Optuna](https://optuna.org/)
against historical trade data, evaluated on out-of-sample windows to guard against overfitting, and
deployed as an always-on live-trading process on [Fly.io](https://fly.io/).

> **Status: concluded.** The research goal (a strategy that reliably
> beats buy-and-hold after fees) was not met. Daily-bar trend-following over 2019–2026 BTC/GBP data
> produced risk-adjusted returns _below_ simply holding BTC across every parameter set tested — the
> apparent "downside protection" was just a beta below 1, not genuine alpha. See the
> [conclusion](#conclusion) below.

---

## What it does

- **Ingests** historical trade data from Kraken and stores it locally (SQLite) and in the cloud (Supabase / Postgres).
- **Backtests** indicator-based strategies, resampling raw trades into OHLC bars at any interval.
- **Optimises** strategy parameters with Optuna, using a walk-forward in-sample / out-of-sample split.
- **Trades live** on Kraken via an always-on executor with order reconciliation and crash recovery.
- **Visualises** everything through a [NiceGUI](https://nicegui.io/) dashboard.

## What's inside

Production code lives under `scalper/`:

| Module                | Responsibility                                                               |
| --------------------- | ---------------------------------------------------------------------------- |
| `data_system/`        | Storage layer — repository pattern over dual SQLite/Supabase backends.       |
| `exchange_connector/` | Kraken integration via a layered Client → Service → Connector design.        |
| `strategy_manager/`   | Indicators, rules, and strategies with dual live/vectorised implementations. |
| `backtesting_engine/` | Optuna optimisation, profit calculation, out-of-sample evaluation.           |
| `trade_executor/`     | Live-trading loop, position sizing, order reconciliation, state recovery.    |
| `study_analyser/`     | Optuna study analysis and plotting.                                          |
| `ui/`                 | NiceGUI dashboard.                                                           |
| `scripts/`            | CLI entry points (not importable production code).                           |

Architecture, conventions, and design decisions are documented in detail under `docs/`
(see [Documentation](#documentation)).

## Tech stack

Python 3.12+ · Optuna · pandas / NumPy · SQLAlchemy + SQLite · Supabase (Postgres) · NiceGUI ·
Fly.io · managed with [`uv`](https://github.com/astral-sh/uv).

---

## Getting started

```sh
uv sync     # install dependencies
pytest      # run the full test suite
```

Local backtesting and the test suite work without any credentials. Live trading and cloud
storage need a `.env` file in the repo root:

```
KRAKEN_TRADING_API_KEY=...
KRAKEN_TRADING_API_SECRET=...
SUPABASE_URL=...
SUPABASE_KEY=...
```

## Running the parts

Entry points live in `scalper/scripts/`. Run them as modules from inside `scalper/`
(`python -m scripts.<name>`).

**Backtesting & optimisation**

```sh
python -m scripts.run_backtest             # single backtest run
python -m scripts.optimise_in_sample       # Optuna parameter search
python -m scripts.evaluate_out_of_sample   # out-of-sample evaluation of trials
python -m scripts.analyse_study            # study analysis and plots
```

**Dashboard**

```sh
python -m scripts.start_ui                 # NiceGUI dashboard on http://localhost:8080
```

**Live trading** (places real orders — credentials required)

```sh
python -m scripts.start_scalping --bot-id <id>
```

## Tests

`pytest.ini` sets `pythonpath = scalper` and `testpaths = scalper/tests`, so plain `pytest`
works from the repo root.

```sh
pytest                                  # everything
pytest -m strategy_manager              # one module
pytest -m "strategy_manager and rules"  # one sub-category
pytest -m integration                   # integration tests only
```

Unit tests mirror the source layout under `scalper/tests/unit/`; integration tests
(system boundaries mocked, layers run together) live in `scalper/tests/integration/`.

## Documentation

Full module docs are built with [MkDocs](https://www.mkdocs.org/):

```sh
uv run --group docs mkdocs serve   # live-reloading docs at http://localhost:8000
```

They cover each module's design, the Client/Service/Connector and repository patterns, the
production architecture on Fly.io + Supabase, and an
[Architecture Decision Log](docs/architecture-decision-log.md) recording non-obvious trade-offs.

---

## Live deployment

The system wasn't only backtested — it ran **live on Kraken with real capital for ~9 weeks**
(15 Apr → 18 Jun 2026), as a single always-on Fly.io process persisting every interval to
Supabase.

| Metric                  | Value                                              |
| ----------------------- | -------------------------------------------------- |
| Strategy / pair         | `PrecisionTrendStrategy` on BTC/GBP, 1-minute bars |
| Duration                | ~9 weeks, ~93,000 one-minute intervals             |
| Orders                  | 23 placed, 23 filled, 0 failed                     |
| Capital                 | modest, real (a deliberate small-stake smoke test) |
| BTC/GBP over the window | −12.8% (≈£54.5k → £47.5k; ranged £44k–£61k)        |
| **Strategy return**     | **−10.3%**                                         |
| **Buy-and-hold return** | **−12.8%**                                         |
| Trading fees            | ≈9% of starting capital — a material drag          |

The run confirmed the backtest verdict rather than contradicting it. The strategy "beat"
buy-and-hold by ~2.5 points, but only by _losing less_ in a falling market — exactly the
beta-below-1 cushioning identified in the research, not genuine alpha. It still lost money in
absolute terms, and fee drag on a small account was significant. As an _engineering_ exercise,
though, the run did what it was built to do: deploy, run unattended for two months, and
reconcile every one of its orders without a single failure.

## Conclusion

The strategies in this repository do **not** reliably beat buy-and-hold on BTC/GBP after realistic
fees. The final experiment (daily-bar trend-following, evaluated on ~2,700 daily bars spanning the
2021 bull, 2022 bear, 2023 recovery, 2024 bull, 2025 flat, and 2026 downtrend) was rejected: its
risk-adjusted return (Sortino) sat below buy-and-hold across all parameter sets and both fee
assumptions. What looked like downside protection was a beta below 1, not alpha — a verdict the
[live deployment](#live-deployment) then confirmed with real money.

That is a perfectly ordinary result for retail technical-analysis strategies, and the project is
treated as concluded for profit-seeking purposes. It remains a worked example of building a
research-to-production system properly: layered architecture, a repository abstraction over two
storage backends, dual live/vectorised strategy implementations with parity tests, walk-forward
out-of-sample validation, and an extensive test suite.
