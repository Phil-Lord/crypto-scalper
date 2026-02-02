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

## Exchange Connector

| Decision                                    | Rationale                                                                                                                                             |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Three-layer architecture (API/Service/Connector) | Separates HTTP concerns from business logic from public interface; enables mocking at each layer for testing                                    |
| Retry with exponential backoff              | Kraken rate limits are strict; automatic retries with backoff prevent failures during high-volume operations like bulk trade fetching                 |
| Optional client injection in connectors     | Allows default instantiation for production use while enabling mock injection for tests                                                               |
| Domain object conversion in connectors      | Connectors are the boundary between external API and internal domain; keeps raw API formats out of business logic                                     |
| Keep connector layer despite simple delegation | Connectors provide platform-agnostic interface for future multi-exchange support; even thin wrappers add strategic value by establishing stable public API and natural home for domain logic |
| Add domain models only when necessary | Not all connectors need domain objects; add them when they provide value (type safety, transformation logic, multi-exchange abstraction, persistence preparation). Balance abstraction with pragmatism. |
| Exchange models in `exchange_connector/models/` | Domain models representing exchange API responses live in `exchange_connector/models/` as they're exchange-specific concepts, not database entities. Exception: if raw API response exactly matches database schema (like `Trade`), the model can live in `data_system/models/` to avoid duplication. |

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
