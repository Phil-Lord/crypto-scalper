# CLAUDE.md — Agent Orientation

Crypto scalping bot. Production code lives entirely under `scalper/`. Legacy code under `legacy/`
is unmaintained — ignore it unless explicitly asked.

---

## Project Structure

```
scalper/
├── backtesting_engine/     # Optuna parameter optimisation, profit calc, generalisation evaluation
├── core/                   # Job runner (async helpers for thread/subprocess jobs)
├── data_system/            # Storage layer: SQLAlchemy (SQLite local) + Supabase (cloud)
│   ├── clients/            # SQLAlchemyClient, SupabaseClient
│   ├── config/             # LocalSQLiteConfig, SupabaseConfig
│   ├── models/             # Dataclasses: Bot, BotOrder, BotRun, BotTick, Job, Trade, ...
│   ├── repositories/       # One folder per aggregate (bot, bot_order, job, trade, ...)
│   └── schema.sql          # Postgres and local SQLite schema
├── exchange_connector/     # Kraken integration
│   ├── api/                # KrakenApiClient + exceptions
│   ├── connectors/         # Public interface — high-level callable units
│   ├── services/           # Lower-level service objects used by connectors
│   ├── kraken_utils/       # Auth/signature helpers
│   └── models/             # AddOrderResult, OhlcCandle, QueryOrderResult, ...
├── strategy_manager/       # Strategies, indicators, rules + factory
│   ├── factory.py          # create_strategy(), STRATEGIES registry
│   ├── indicators/         # SMA, EMA, RSI, ADX, ATR
│   ├── rules/              # MA crossover, RSI/ADX/ATR thresholds
│   └── strategies/         # SmaStrategy, PrecisionTrendStrategy (each with *_config.py)
├── study_analyser/         # Optuna study analysis + plotting
├── trade_executor/         # Live trading loop, position sizers, order reconciliation
├── ui/                     # NiceGUI app (pages, components, services, theme, static)
├── utils/                  # load_env, LOG_FORMAT, pair_config, timestamps, optuna helpers,
│                           #   strategy_configs, data_visualisation
├── scripts/                # CLI entry points (NOT importable production code)
├── local_storage/          # SQLite DB lives here (scalper.db)
├── logs/                   # Runtime logs
└── tests/
    ├── unit/               # Mirrors source structure
    └── integration/        # Flat files, cross-layer tests
```

Test files mirror source paths: `strategy_manager/foo.py` → `tests/unit/strategy_manager/test_foo.py`.

Public APIs are re-exported from each module's `__init__.py` (e.g. `from data_system import SupabaseClient`).
Cross-module imports should use the package, not deep paths.

---

## Running Tests

`pytest.ini` sets `pythonpath = scalper` and `testpaths = scalper/tests`, so plain `pytest` works
from the repo root (or from inside `scalper/`).

```bash
pytest                                  # everything
pytest -m strategy_manager              # one module
pytest -m "strategy_manager and rules"  # one sub-category
pytest -m integration                   # all integration tests
pytest scalper/tests/unit/strategy_manager/rules/test_ma_crossover_rule.py  # one file
pytest -k crossover                     # by name
```

See `pytest.ini` for the full marker list (one per module, sub-category, class, and often
per-method).

---

## Things to Be Careful About

These are conventions, not all currently enforced by tooling — break them only with reason.

- **`logging.basicConfig()` belongs in `scripts/` only.** Library/service modules use
  `logging.getLogger(__name__)` and let the entry point configure handlers. `start_scalping.py`
  shows the pattern (set root to WARNING, raise app-package loggers via `LOG_LEVEL` env var).
- **Call `utils.load_env()` at the top of every script** before importing modules that read env
  vars at import time (Supabase, Kraken). It's a no-op in production where env comes from the
  platform.
- **Never run `scripts/start_scalping.py` without explicit user instruction.** This places real
  orders on Kraken.
- **Don't modify `data_system/schema.sql`** without explicit instruction — it's the SQLite source
  of truth and changes need to land in lockstep with repository code and any cloud Supabase
  changes.
- **British English in code, comments, docs, and identifiers** — `optimise`, `analyse`,
  `serialise`, `generalisation`. The codebase is consistent on this; don't introduce `-ize`
  spellings.

---

## When to Ask vs Proceed

**Proceed without asking:**

- Adding/updating tests, fixing style, refactoring within a module
- Reading any file to gather context
- Adding new indicators, rules, or strategies (follow patterns in
  `strategy_manager/{indicators,rules,strategies}/`)
- Local-only changes to UI pages/components

**Ask first:**

- Changing public APIs (anything re-exported from a module's `__init__.py`)
- Adding new dependencies (`uv add <package>` — don't hand-edit `pyproject.toml`)
- Changes that touch `data_system/schema.sql` and application code together
- Anything in `trade_executor/` or `scripts/start_scalping.py` (live trading paths)
- Modifying `.env`, fly.toml, Dockerfile, or anything deployment-shaped

---

## Environment

- Python 3.13.4 (`.python-version`); `pyproject.toml` requires ≥3.12. Managed by `uv`.
- Install deps: `uv sync` (use `uv sync --group docs` for mkdocs deps).
- Local DB: SQLite at `scalper/local_storage/scalper.db`.
- Cloud DB: Supabase — needs `SUPABASE_URL` + `SUPABASE_KEY` in `.env`.
- Exchange: Kraken — needs `KRAKEN_API_KEY` + `KRAKEN_API_SECRET` in `.env`.
- UI: NiceGUI app started via `scripts/start_ui.py` (port 8080).
- Docs: `mkdocs serve` (config at repo root `mkdocs.yml`).

---

## Useful Entry Points (`scalper/scripts/`)

**Trading & UI**

- `start_scalping.py` — live trading loop (DO NOT run unprompted)
- `start_ui.py` — NiceGUI dashboard

**Backtesting & Optuna**

- `run_backtest.py` — single backtest run
- `find_param_sets.py` — Optuna parameter search
- `analyse_study.py`, `delete_study.py` — Optuna study management

**Bot & job management**

- `register_bot.py` — register a bot config in Supabase
- `manage_jobs.py` — inspect/modify the job queue
- `query_supabase.py` — ad-hoc Supabase queries

**Kraken API helpers**

- `fetch_trades.py`, `get_trades.py`, `get_ticker.py`, `get_balances.py`, `get_asset_pairs.py`, `add_order.py`, `query_orders.py`
