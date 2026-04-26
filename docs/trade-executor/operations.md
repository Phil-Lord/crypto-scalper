# Operations

Day-to-day workflows for the live-trading process. Architecture lives in the
[Trade Executor index](index.md); platform-level setup lives in
[Cloud Architecture](../cloud-architecture.md).

## Running Locally via Docker

Useful for verifying the image before `fly deploy`, or running a dry run against production
Kraken/Supabase from your machine.

```sh
docker build -t crypto-scalper .

# Live (against real exchange) — careful
docker run --env-file .env -e BOT_IDS=btc_1m_001 crypto-scalper

# Dry run — Kraken validates orders, nothing persisted
docker run --env-file .env -e BOT_IDS=btc_1m_001 -e DRY_RUN=true crypto-scalper
```

`BOT_IDS` is not a secret and is **not** in `.env` — pass it with `-e`. All other vars
(`KRAKEN_TRADING_API_KEY`, `KRAKEN_TRADING_API_SECRET`, `SUPABASE_URL`, `SUPABASE_KEY`)
come from `.env`. The `.dockerignore` keeps `.env` out of the image; it is injected only
at `docker run` time.

## Deploying Code Updates

`fly deploy` is the only deployment command. The full lifecycle:

1. `fly deploy` builds and pushes the new image.
2. Fly.io sends `SIGTERM` to the running container.
3. Signal handler calls `executor.request_shutdown()` on each executor — any in-flight
   `execute_interval()` completes (including its order placement and QueryOrders retry
   loop); subsequent firings return immediately.
4. `scheduler.shutdown(wait=True)` blocks until running jobs finish.
5. `executor.shutdown()` marks each `BotRun` as `completed_at = now()`.
6. Process exits, old container removed.
7. New container starts → `entrypoint.sh` → `start_scalping.py`.
8. For each bot: `warm_up()` replays OHLC history; `recover_state()` restores
   `last_action` from the latest directional tick.
9. Scheduler starts. Bots resume on the next wall-clock-aligned interval.

**Safety guarantees:**

- No order placement is interrupted mid-flight (graceful drain).
- At most one interval is missed during the swap (~30s).
- All state is recovered from Supabase — no in-memory state is lost.
- `BotRun` records cleanly delineate pre- and post-deploy activity.

## Adding a New Bot

```sh
# Run from the repo root. PYTHONPATH=scalper makes the top-level packages
# (data_system, utils, ...) resolvable — the Dockerfile sets the same var
# in production.
PYTHONPATH=scalper uv run python -m scripts.register_bot \
  --id eth_5m_v2 \
  --pair XETHZGBP \
  --strategy-name PrecisionTrendStrategy \
  --strategy-version v1.0.0 \
  --interval 5 \
  --parameters '{"short_ema": 43, ...}'

fly secrets set BOT_IDS=btc_1m_001,eth_5m_v2
fly deploy
```

The new bot starts with `recover_state()` finding no previous tick (first run, defaults
to `last_action = SELL`), warms up from OHLC history, then begins trading. Existing bots
recover from their latest ticks and resume. **No code changes are required** — bot
configuration lives entirely in the `bots` table.

## Removing a Bot

```sh
fly secrets set BOT_IDS=btc_1m_001
fly deploy
```

The removed bot's last `BotRun` was already marked complete during the graceful shutdown
of the prior deployment. Its history (`bot_ticks`, `bot_orders`, `bot_runs`) stays in
Supabase for analysis; the `Bot` row may be left in place — only IDs in `BOT_IDS` are
launched.

## Updating Bot Parameters

Parameters are read from Supabase once during `TradeExecutor` construction. To change
them:

1. Update the `Bot` row in Supabase (directly via SQL or a future `update_bot.py`).
2. `fly deploy` (or `fly apps restart crypto-scalper`).

Changing the row mid-run has no effect — the bot only re-reads parameters on restart.

## Crash Recovery

Fly.io auto-restarts the container on crash, typically <30s. The recovery sequence is the
same as a planned deploy except the previous run never reached `executor.shutdown()`, so
its `BotRun` row is left with `completed_at IS NULL` — useful for monitoring.

`_reconcile_placed_orders()` runs at the start of the first `execute_interval()` after
restart: any orders left in PLACED status from the crashed run are checked against Kraken
and resolved (FILLED or FAILED).

**Worst case:** one missed interval.

## Health Monitoring

Bot heartbeat — should advance every interval:

```sql
SELECT bot_id, MAX(timestamp) AS last_tick
FROM bot_ticks
GROUP BY bot_id;
```

A gap exceeding the bot's interval + grace window indicates a problem worth checking via
`fly logs`. Persistent gaps during OHLC failures are expected — those intervals are
deliberately skipped.

Crashed runs:

```sql
SELECT id, bot_id, started_at
FROM bot_runs
WHERE completed_at IS NULL;
```

Outstanding orders awaiting reconciliation:

```sql
SELECT id, bot_id, exchange_order_id, placed_at
FROM bot_orders
WHERE status = 'placed'
ORDER BY placed_at;
```

A row that has been `placed` for many intervals usually means Kraken returned a status
`QueryOrdersConnector` does not recognise — check `fly logs` and either reconcile manually
or add the status to `QueryOrderStatus`.

## Toggling Log Level

```sh
fly secrets set LOG_LEVEL=DEBUG
fly apps restart crypto-scalper

# Revert
fly secrets unset LOG_LEVEL
fly apps restart crypto-scalper
```

`DEBUG` surfaces routine HOLD-interval completions and the "no placed orders to reconcile"
message — useful for diagnosing missed intervals or scheduler issues. No code change or
redeploy required.
