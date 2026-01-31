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

Records executed trades.

| Column        | Type        | Description               |
| ------------- | ----------- | ------------------------- |
| `id`          | UUID (PK)   | Auto-generated order ID   |
| `bot_id`      | TEXT (FK)   | References `bots.id`      |
| `run_id`      | UUID (FK)   | References `bot_runs.id`  |
| `tick_id`     | BIGINT (FK) | References `bot_ticks.id` |
| `side`        | TEXT        | `'buy'` or `'sell'`       |
| `price`       | DECIMAL     | Execution price           |
| `volume`      | DECIMAL     | Trade volume              |
| `fee`         | DECIMAL     | Fee charged (nullable)    |
| `executed_at` | TIMESTAMPTZ | Execution timestamp       |

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

### `generalisation_evaluation`

Stores out-of-sample evaluation results for Optuna trials.

| Column            | Type          | Description                    |
| ----------------- | ------------- | ------------------------------ |
| `study_name`      | TEXT (CPK)    | Optuna study name              |
| `trial_number`    | INTEGER (CPK) | Trial number within the study  |
| `start_timestamp` | FLOAT (CPK)   | Evaluation window start        |
| `end_timestamp`   | FLOAT (CPK)   | Evaluation window end          |
| `final_balance`   | FLOAT NOT NULL | Final balance after evaluation |
| `geo_mean_return` | FLOAT NOT NULL | Geometric mean return          |

---

## Indexing Strategy

Critical indexes are defined for common query patterns:

| Table       | Index                          | Purpose                                    |
| ----------- | ------------------------------ | ------------------------------------------ |
| `trades`    | `(pair, timestamp)`            | Fast fetching of trades within time ranges |
| `bot_runs`  | `(bot_id, started_at DESC)`    | Quick lookup of recent runs per bot        |
| `bot_ticks` | `(run_id, timestamp ASC)`      | Instant chart loading for a run            |
| `bot_ticks` | `(id) WHERE error IS NOT NULL` | Fast error debugging                       |

---

## Data Integrity Constraints

- **Immutable Models:** All dataclasses use `frozen=True` to prevent mutation after creation.
- **CHECK Constraints:** `bot_ticks.signal` restricted to `('buy', 'sell', 'hold')`;
  `bot_orders.side` restricted to `('buy', 'sell')`.
- **Cascade Deletes:** Deleting a `bot_run` cascades to its `bot_ticks` and `bot_orders`.
