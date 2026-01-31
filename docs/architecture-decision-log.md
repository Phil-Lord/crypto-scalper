# Architecture Decision Log

This document captures architectural decisions that aren't immediately obvious from the code.
Record decisions here when future-you might ask _"why did I do it this way?"_.

---

## System-wide

| Decision                                    | Rationale                                                                                                                    |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Use `datetime` (not `float`) for timestamps | Human-readable when debugging; PostgreSQL `TIMESTAMPTZ` has powerful time functions; Python `datetime` can be timezone-aware |
| Always use timezone-aware UTC               | Avoids ambiguity; consistent across systems; required for `TIMESTAMPTZ`                                                      |
| Use `Decimal` for live trading money        | Precision matters for real transactions; `float` is fine for backtesting where speed > precision                             |

---

## Data System

| Decision                                             | Rationale                                                                                                                                   |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Denormalise `bot_id` on `bot_ticks`                  | Read performance is critical for time-series data; avoids JOIN on `bot_runs` for common query _"all ticks for bot X"_; enables partitioning |
| Composite primary key `(trade_id, pair)` on `trades` | Kraken trade IDs are only unique within a trading pair                                                                                      |
| Dual backend (SQLite + PostgreSQL)                   | SQLite for fast local backtesting; PostgreSQL/Supabase for durable cloud storage and Lambda integration                                     |

---

## Trade Executor

| Decision     | Rationale |
| ------------ | --------- |
| _(None yet)_ |           |

---

## Backtesting Engine

| Decision     | Rationale |
| ------------ | --------- |
| _(None yet)_ |           |

---

## Strategy Manager

| Decision     | Rationale |
| ------------ | --------- |
| _(None yet)_ |           |
