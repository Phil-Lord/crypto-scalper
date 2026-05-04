# Schema Reference

## Live Trading Tables (PostgreSQL/Supabase)

These tables support the [Cloud Architecture](../cloud-architecture.md) and record all live trading
activity.

### `bots`

Defines bot configurations - the "who" and "how".

| Column             | Type        | Description                         |
| ------------------ | ----------- | ----------------------------------- |
| `id`               | TEXT (PK)   | Human-readable ID, e.g. `btc_1m_v1` |
| `pair`             | TEXT        | Trading pair, e.g. `XXBTZGBP`       |
| `strategy_name`    | TEXT        | Strategy class name                 |
| `strategy_version` | TEXT        | Version identifier                  |
| `interval`         | INTEGER     | Interval in minutes                 |
| `parameters`       | JSONB       | Strategy parameters                 |
| `created_at`       | TIMESTAMPTZ | Creation timestamp                  |

### `bot_runs`

Tracks execution sessions - every time a bot is "turned on".

| Column         | Type        | Description                   |
| -------------- | ----------- | ----------------------------- |
| `id`           | UUID (PK)   | Auto-generated run ID         |
| `bot_id`       | TEXT (FK)   | References `bots.id`          |
| `started_at`   | TIMESTAMPTZ | When the run started          |
| `completed_at` | TIMESTAMPTZ | When the run ended (nullable) |

### `bot_ticks`

Records granular interval results - the immutable record of each trading decision.

| Column          | Type           | Description                       |
| --------------- | -------------- | --------------------------------- |
| `id`            | BIGSERIAL (PK) | Auto-incrementing ID              |
| `bot_id`        | TEXT (FK)      | Denormalised for faster filtering |
| `run_id`        | UUID (FK)      | References `bot_runs.id`          |
| `timestamp`     | TIMESTAMPTZ    | The heartbeat timestamp           |
| `price`         | DECIMAL        | Market price at tick              |
| `signal`        | TEXT           | `'buy'`, `'sell'`, or `'hold'`    |
| `error`         | TEXT           | Error message if any (nullable)   |
| `balance_base`  | DECIMAL        | Base currency balance             |
| `balance_quote` | DECIMAL        | Quote currency balance            |

### `bot_orders`

Records orders placed by a bot, with explicit lifecycle. See
[Trade Executor → Order Lifecycle](../trade-executor/index.md#order-lifecycle) for the
state machine.

| Column              | Type                   | Description                                                              |
| ------------------- | ---------------------- | ------------------------------------------------------------------------ |
| `id`                | UUID (PK)              | Auto-generated order ID                                                  |
| `bot_id`            | TEXT (FK)              | References `bots.id`                                                     |
| `run_id`            | UUID (FK)              | References `bot_runs.id` (cascade delete)                                |
| `tick_id`           | BIGINT (FK, nullable)  | References `bot_ticks.id`; linked after the tick is persisted            |
| `exchange_order_id` | TEXT                   | Kraken order ID (`txid`); domain-layer name disambiguates from trade IDs |
| `side`              | TEXT                   | `'buy'` or `'sell'`                                                      |
| `status`            | TEXT                   | `'placed'`, `'filled'`, or `'failed'` (default `'placed'`)               |
| `placed_at`         | TIMESTAMPTZ            | When the order was submitted to the exchange (default `NOW()`)           |
| `filled_at`         | TIMESTAMPTZ (nullable) | When the order reached a terminal state (FILLED or FAILED)               |
| `price`             | DECIMAL (nullable)     | Average executed price (set on FILL; may be present on FAILED)           |
| `volume`            | DECIMAL (nullable)     | Executed volume                                                          |
| `fee`               | DECIMAL (nullable)     | Fee paid                                                                 |

---

## Backtesting Tables (SQLite)

These tables support local parameter optimisation and strategy evaluation.

### `trades`

Historical trade data fetched from Kraken API.

| Column       | Type         | Description                            |
| ------------ | ------------ | -------------------------------------- |
| `trade_id`   | BIGINT (CPK) | Trade ID from Kraken (unique per pair) |
| `pair`       | TEXT (CPK)   | Trading pair, e.g. `XXBTZGBP`          |
| `price`      | FLOAT        | Execution price                        |
| `volume`     | FLOAT        | Trade volume                           |
| `timestamp`  | FLOAT        | Unix timestamp (sub-second precision)  |
| `side`       | TEXT         | `'b'` (buy) or `'s'` (sell)            |
| `order_type` | TEXT         | `'m'` (market) or `'l'` (limit)        |

> **Note:** Primary key is composite `(trade_id, pair)` since Kraken trade IDs are only unique
> within a trading pair.

### `out_of_sample_evaluation`

Stores out-of-sample evaluation results for Optuna trials.

| Column            | Type           | Description                                                    |
| ----------------- | -------------- | -------------------------------------------------------------- |
| `study_name`      | TEXT (CPK)     | Optuna study name                                              |
| `trial_number`    | INTEGER (CPK)  | Trial number within the study                                  |
| `start_timestamp` | FLOAT (CPK)    | Evaluation period start (Unix seconds)                         |
| `end_timestamp`   | FLOAT (CPK)    | Evaluation period end (Unix seconds)                           |
| `geo_mean_return` | FLOAT NOT NULL | Geometric mean of per-window return ratios over the OOS period |

### `jobs`

Tracks background jobs (e.g., trade fetching, backtest runs) submitted via `scripts/manage_jobs.py`.

| Column       | Type      | Description                                           |
| ------------ | --------- | ----------------------------------------------------- |
| `id`         | TEXT (PK) | Job UUID stored as text                               |
| `job_type`   | TEXT      | `'get_trades'`, `'fetch_trades'`, or `'run_backtest'` |
| `status`     | TEXT      | `'pending'`, `'running'`, `'done'`, or `'error'`      |
| `message`    | TEXT      | Optional status detail or error message (nullable)    |
| `created_at` | FLOAT     | Unix timestamp of creation                            |
| `updated_at` | FLOAT     | Unix timestamp of last status change                  |

---

## Indexing Strategy

Critical indexes are defined for common query patterns:

| Table       | Index                          | Purpose                                    |
| ----------- | ------------------------------ | ------------------------------------------ |
| `trades`    | `(pair, timestamp)`            | Fast fetching of trades within time ranges |
| `trades`    | `(pair)`                       | Pair-only filtering without time bounds    |
| `bot_runs`  | `(bot_id, started_at DESC)`    | Quick lookup of recent runs per bot        |
| `bot_ticks` | `(run_id, timestamp ASC)`      | Instant chart loading for a run            |
| `bot_ticks` | `(id) WHERE error IS NOT NULL` | Fast error debugging                       |

---

## Data Integrity Constraints

- **Immutable Models:** All dataclasses use `frozen=True` to prevent mutation after creation.
  Updates to `BotOrder` (e.g. status transitions, filling in `tick_id`) use
  `dataclasses.replace()`.
- **CHECK Constraints:** `bot_ticks.signal` restricted to `('buy', 'sell', 'hold')`;
  `bot_orders.side` restricted to `('buy', 'sell')`; `bot_orders.status` restricted to
  `('placed', 'filled', 'failed')`.
- **Cascade Deletes:** Deleting a `bot_run` cascades to its `bot_ticks` and `bot_orders`.
