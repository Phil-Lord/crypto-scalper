# CLAUDE.md — Agent Orientation

Crypto scalping bot. Production code lives entirely under `scalper/`. Legacy code under `legacy/`
is not maintained — ignore it unless asked.

---

## Key Commands

```bash
# Run all tests
cd scalper && make test

# Run a specific module's tests
make test/data_system
make test/exchange_connector
make test/strategy_manager
make test/backtesting_engine
make test/utils

# Run sub-category tests
make test/data_system/repositories
make test/exchange_connector/connectors
make test/strategy_manager/indicators
make test/strategy_manager/rules
make test/strategy_manager/strategies

# Run integration tests only
make test/integration
make test/integration/exchange_connector
make test/integration/strategy_manager
make test/integration/backtesting_engine
```

---

## Project Structure

```
scalper/
├── backtesting_engine/     # Local parameter optimisation (Optuna)
├── data_system/            # Storage: SQLite (local) + Supabase (cloud)
├── exchange_connector/     # Kraken API (connectors/ is the public interface)
├── strategy_manager/       # Strategies, indicators, rules
├── study_analyser/         # Optuna study analysis and plotting
├── trade_executor/         # Live trading execution loop
├── utils/                  # Shared utilities (timestamp, env vars, pair config, Optuna utils, data visualisation, strategy configs)
├── scripts/                # Entry-point scripts (not production code)
└── tests/
    ├── unit/               # Mirror source structure
    └── integration/        # Flat files, cross-layer tests
```

Tests mirror source: `strategy_manager/foo.py` → `tests/unit/strategy_manager/test_foo.py`

---

## Non-Negotiable Rules

- **Never call `logging.basicConfig()`** in library/service code — only in `scripts/` entry points
- **Call `load_env()` before** importing any module that reads env vars at import time
- **Never run `scripts/start_scalping.py`** without explicit user instruction — this triggers live trading
- **Never modify database schema** (`schema.sql` or migrations) without explicit instruction
- **British English** everywhere — optimise, analyse, serialise, centralise (not -ize/-ize)

---

## When to Ask vs Proceed

**Proceed without asking:**

- Adding tests, fixing style, refactoring within a module
- Reading any file to gather context
- Adding new indicators, rules, or a strategy (see `.github/prompts/add-strategy.prompt.md`)

**Ask first:**

- Changing public APIs (method signatures exported by `__init__.py`)
- Adding new dependencies to `pyproject.toml` (use `uv add <package>`)
- Changes that touch both `data_system` schema and application code simultaneously
- Anything that touches live trading paths (`trade_executor/`, `scripts/start_scalping.py`)

---

## Adding New Things

Reusable prompts in `.github/prompts/`:

- **`audit-module.prompt.md`** — Audit a module against project standards
- **`new-module.prompt.md`** — Scaffold a new module from scratch
- **`add-strategy.prompt.md`** — Add a new trading strategy
- **`new-feature.prompt.md`** — Checklist for shipping a complete feature
- **`review-instructions.prompt.md`** — Sync instructions and prompts with the codebase

---

## Environment

- Python 3.13.4 (managed by uv, see `.python-version`)
- Dependencies: `pyproject.toml` + `uv.lock` (use `uv sync` to install)
- Local DB: SQLite at `scalper/local_storage/scalper.db`
- Cloud DB: Supabase (requires `SUPABASE_URL` + `SUPABASE_KEY` in `.env`)
- Exchange: Kraken (requires `KRAKEN_API_KEY` + `KRAKEN_API_SECRET` in `.env`)
