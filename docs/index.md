# Scalper

A crypto scalping bot. Indicator-based strategies are tuned by Optuna against historical
trade data, evaluated on out-of-sample windows, and deployed as an always-on live-trading
process on Fly.io.

The codebase is split into focused modules; this site documents the design, conventions,
and operational workflows of each.

## Sections

| Section                                                   | What's in it                                                                                         |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| [Data System](data-system/index.md)                       | Storage layer — repositories, dual SQLite/Supabase backends, schema reference.                       |
| [Exchange Connector](exchange-connector/index.md)         | Kraken integration — three-layer Client/Service/Connector pattern and per-endpoint reference.        |
| [Strategy Manager](strategy-manager/index.md)             | Indicators, rules, and strategies — dual live/vectorised computation modes and a guide for new ones. |
| [Backtesting Engine](backtesting-engine/index.md)         | Optuna parameter optimisation, profit calculation, and out-of-sample evaluation.                     |
| [Trade Executor](trade-executor/index.md)                 | Live-trading engine — warm-up, state recovery, order lifecycle, and operational workflows.           |
| [Cloud Architecture](cloud-architecture.md)               | How the system runs in production on Fly.io + Supabase.                                              |
| [Architecture Decision Log](architecture-decision-log.md) | Non-obvious design decisions across all modules with their rationale.                                |

## Working on the docs

```sh
uv run --group docs mkdocs serve   # live-reloading server
uv run --group docs mkdocs build   # static build into ./site
```
