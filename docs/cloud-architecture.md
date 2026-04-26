# Cloud Architecture

How the live-trading scalper runs in production. Operational workflows
(`fly deploy`, adding bots, monitoring) live in
[Trade Executor → Operations](trade-executor/operations.md).

## Execution Model

The scalper runs as an **always-on** Python process, one Fly.io Machine for the whole fleet.
APScheduler fires a `TradeExecutor.execute_interval()` per bot on each candle close, with
indicator state held warm in memory between intervals.

```
Fly Machine
└── entrypoint.sh
    └── start_scalping.py
        └── BlockingScheduler (APScheduler, CronTrigger)
            ├── TradeExecutor.execute_interval()  ← bot 1 (e.g. 1m, BTCGBP)
            ├── TradeExecutor.execute_interval()  ← bot 2 (e.g. 5m, ETHGBP)
            └── …
```

Always-on (rather than stateless per-interval invocations) is the deliberate choice — see
[Architecture Decision Log](architecture-decision-log.md). In short: EMAs are infinite
impulse response filters and never fully converge from a cold start. Warming up once on
boot and keeping state in memory eliminates per-interval seed bias and halves Kraken API
calls.

## Compute — Fly.io

| Resource          | Value                  |
| ----------------- | ---------------------- |
| Region            | `lhr` (London)         |
| Machine size      | `shared-cpu-1x`, 512MB |
| Restart policy    | `on-failure`           |
| `kill_timeout`    | 60s (graceful drain)   |
| `auto_stop`       | disabled               |

`auto_stop_machines` is explicitly disabled in `fly.toml` — without inbound HTTP traffic,
Fly would otherwise pause the machine. `kill_timeout = 60` gives the signal handler time to
finish any in-flight `execute_interval()` before SIGKILL.

Cost target: ~$2/month for 2-5 bots in one process. Migrating to one Machine per bot
(Fly.io Machines API) is straightforward later — only the entry-point changes.

## Container Deployment

The image is built from a single multi-stage `Dockerfile` at the repo root. Key points:

- **Base:** `python:3.13-slim`.
- **Dependencies:** `uv sync --locked --no-group dev --no-group docs` — test and docs
  tooling stay out of the image.
- **Source layout:** only the production packages are copied (`data_system`,
  `exchange_connector`, `strategy_manager`, `trade_executor`, `utils`, plus the single
  `start_scalping.py` script).
- **Entrypoint:** `entrypoint.sh` parses comma-separated `BOT_IDS` and `DRY_RUN`
  environment variables into the right CLI flags for `start_scalping.py`.

`fly deploy` is the only deployment command — it builds, pushes, and rolls the machine.

## Database — Supabase

Supabase (PostgreSQL) stores all live-trading data. The free tier is sufficient at current
volume.

The data model:

```
bots (1) ──► bot_runs (many) ──► bot_ticks (many)
                              └─► bot_orders (many)
```

| Table        | Purpose                                                                          |
| ------------ | -------------------------------------------------------------------------------- |
| `bots`       | Configuration identity (pair, strategy, version, params)                         |
| `bot_runs`   | Execution sessions; `completed_at IS NULL` indicates a crashed run               |
| `bot_ticks`  | Per-interval decisions (the immutable record); also drives health monitoring     |
| `bot_orders` | Orders with explicit `placed → filled / failed` lifecycle and `exchange_order_id`|

`bot_id` (`btc_1m_v1`) is the configuration-level identity; `run_id` is the execution
identity, allowing reuse across restarts. Bot configuration is read from the `bots` table
at process start — adding a bot is a database insert, not an infrastructure change.

> Full schema, indexes, and constraints: [Schema Reference](data-system/schema-reference.md).

## Configuration & Secrets

All credentials are stored as Fly.io secrets and surface as environment variables in the
container:

```sh
fly secrets set \
  KRAKEN_TRADING_API_KEY=… \
  KRAKEN_TRADING_API_SECRET=… \
  SUPABASE_URL=… \
  SUPABASE_KEY=… \
  BOT_IDS=btc_1m_001,eth_5m_v2
```

`BOT_IDS` is the only non-secret env var — it controls which bots the entrypoint launches.
`DRY_RUN=true` switches every bot into Kraken's `validate=True` mode and disables tick
persistence.

`SupabaseConfig` reads env vars lazily via metaclass properties, so import order in scripts
does not depend on `load_env()` running first.

## Logging

Plain text logging via `LOG_FORMAT` to stderr — `fly logs` captures and exposes them. Each
log line is prefixed with the bot id via a `LoggerAdapter`, which is critical for tracing
multi-bot processes.

The application log level is configured via the `LOG_LEVEL` env var
(`fly secrets set LOG_LEVEL=DEBUG` + `fly apps restart` to surface routine HOLD intervals
and reconciliation no-ops). The root logger stays at WARNING to suppress noise from
`httpcore`, `hpack`, etc.

JSON structured logging is deferred until a log aggregation sink (Datadog, Loki) is added —
a one-line change in the entry-point formatter.
