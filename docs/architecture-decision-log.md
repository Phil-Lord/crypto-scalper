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

| Decision                                         | Rationale                                                                                                                                                                                                                                                                                             |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Three-layer architecture (API/Service/Connector) | Separates HTTP concerns from business logic from public interface; enables mocking at each layer for testing                                                                                                                                                                                          |
| Retry with exponential backoff                   | Kraken rate limits are strict; automatic retries with backoff prevent failures during high-volume operations like bulk trade fetching                                                                                                                                                                 |
| Optional client injection in connectors          | Allows default instantiation for production use while enabling mock injection for tests                                                                                                                                                                                                               |
| Domain object conversion in connectors           | Connectors are the boundary between external API and internal domain; keeps raw API formats out of business logic                                                                                                                                                                                     |
| Keep connector layer despite simple delegation   | Connectors provide platform-agnostic interface for future multi-exchange support; even thin wrappers add strategic value by establishing stable public API and natural home for domain logic                                                                                                          |
| Add domain models only when necessary            | Not all connectors need domain objects; add them when they provide value (type safety, transformation logic, multi-exchange abstraction, persistence preparation). Balance abstraction with pragmatism.                                                                                               |
| Exchange models in `exchange_connector/models/`  | Domain models representing exchange API responses live in `exchange_connector/models/` as they're exchange-specific concepts, not database entities. Exception: if raw API response exactly matches database schema (like `Trade`), the model can live in `data_system/models/` to avoid duplication. |

---

## Backtesting Engine

| Decision                                         | Rationale                                                                                                                                                                                                                         |
| ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Use Optuna for parameter optimisation            | TPE sampler provides efficient Bayesian optimisation; built-in parallelization via PostgreSQL storage; pruning reduces wasted trials; proven in ML hyperparameter tuning with similar search spaces                               |
| Rolling 3-month windows with 1-month steps       | 3 months provides sufficient data for diverse market conditions; 1-month overlap increases sample density; warmup day allows indicators to initialize; longer windows reduce noise, shorter steps increase generalisation testing |
| Geometric mean for multi-window aggregation      | Accounts for compounding effects (returns multiply, not add); penalises inconsistency more than arithmetic mean; one bad window significantly impacts score, encouraging robust strategies                                        |
| Logistic activity penalty (0.3 trades/day ideal) | Empirical finding: ~1 trade per 3 days balances opportunity vs fees; logistic curve provides smooth gradients for Optuna; avoids hard thresholds that create optimisation cliffs; caps at 1.0 to avoid penalising high activity   |
| Concurrent Optuna with constant_liar sampler     | Enables parallel trial execution without lock contention; constant_liar prevents trials from exploring duplicate regions; multivariate=True captures parameter correlations; group=True improves convergence speed                |
| Two-phase evaluation (optimise → generalise)     | Optimisation on one period, evaluation on another prevents overfitting; separate phases allow analysing which parameter sets generalise vs which merely fit training data; supports walk-forward analysis workflow                |
| Dual computation modes (vectorised + iterative)  | Iterative mode tests the same code path used in live trading (row-by-row with stateful indicators), ensuring strategies behave identically in production; vectorised mode uses pandas operations for 10-100x speedup during optimisation; debugging step-through is a secondary benefit |
| Store studies in PostgreSQL not SQLite           | PostgreSQL supports concurrent writes from parallel workers; row-level locking prevents conflicts; connection pooling improves throughput; SQLite would serialise all trial writes                                                |
| 0.04% fee on both sides                          | Matches Kraken maker fees at time of implementation; conservative (actual fees may be lower with volume); applied symmetrically to buy and sell for simplicity                                                                    |

---

## Strategy Manager

| Decision                                       | Rationale                                                                                                                                                                                           |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dual computation modes (live + vectorised)     | Live mode (row-by-row) is what runs in production, so backtesting must support it to verify identical behaviour; vectorised mode uses pandas operations for 10-100x speedup during parameter optimisation; debugging step-through is a secondary benefit |
| Indicators/Rules/Strategies as mutable classes | Live trading requires maintaining state between updates (EMA values, price windows); immutable dataclasses inappropriate for evolving state                                                         |
| Accept code duplication between modes          | Each algorithm implemented twice (stateful vs vectorised); maintenance burden accepted for performance benefits; comprehensive tests ensure parity                                                  |
| Use `Signal` enum from `data_system`           | Type safety across modules; IDE autocomplete; string-compatible for backward compatibility; centralised definition prevents drift                                                                   |
| Bounded state with `deque(maxlen=N)`           | Prevents unbounded memory growth in 24/7 live trading; only store what's needed (window size); constant memory footprint per strategy instance                                                      |
