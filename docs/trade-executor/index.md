# Trade Executor

The trade executor is the live-trading engine. One `TradeExecutor` per bot runs forever
inside a single Fly.io Machine, scheduled by APScheduler. This page describes the
architecture; [Operations](operations.md) covers deploying, adding bots, and monitoring.

## Lifecycle

For each `--bot-id` (the production entrypoint translates the comma-separated
`BOT_IDS` env var into one `--bot-id` flag per id), the entry-point script
(`start_scalping.py`) walks the following sequence once at boot, then hands
control to the scheduler:

```
construct  →  warm_up()  →  recover_state()  →  schedule execute_interval()
                                                       ↓ (every interval, forever)
                                                 execute_interval()
                                                       ↓ (on SIGTERM/SIGINT)
                                            request_shutdown()
                                            scheduler.shutdown(wait=True)
                                                  shutdown()
```

`recover_state()` runs **after** `warm_up()` — the warm-up replay mutates
`strategy.last_action`, and the recovered DB value must overwrite that.

## Construction

`TradeExecutor` is fully dependency-injected. The constructor takes a `Bot`, a
`Strategy`, a `PositionSizer`, the four Supabase repositories, the four Kraken connectors,
and a `dry_run` flag.

It also creates and persists a new `BotRun` immediately on construction. Anything ticks
or orders are linked to belongs to this run; the row's `completed_at` stays `NULL` until
graceful shutdown succeeds, which makes crashed runs trivially detectable.

## Warm-up

`warm_up()` fetches OHLC history, replays each candle through `strategy.generate_signal()`,
and **does not persist ticks** — warm-up signals are mathematically incomplete (EMAs have
not yet converged) and would pollute the decision log.

How much history is required is decided by the strategy itself via the abstract
`Strategy.warmup_candles` property. `PrecisionTrendStrategy` returns
`3 × max(window sizes)` (the standard EMA convergence heuristic — at 3× the window length
the seed value carries ~5% weight); `SmaStrategy` returns `long_window + 1`. Changing
indicator windows in `strategy_configs.py` automatically adjusts the warm-up requirement.

**Kraken's hard cap is 720 candles per OHLC request.** If `warmup_candles > 720`, the
warm-up is partial — `warm_up()` logs a warning and continues. `PrecisionTrendStrategy`'s
maximum is 237 so this only affects an Optuna-optimised `SmaStrategy` with
`long_window > 719`. Solving partial warm-up beyond 720 candles (e.g., from stored local
trades) is deferred.

## State Recovery

`recover_state()` calls `bot_tick_repo.get_latest_action_by_bot_id()` — a query that
filters for `signal IN ('buy', 'sell')`, i.e. the **last directional action**.

Filtering out HOLD ticks is load-bearing: `strategy.last_action` is only ever BUY or SELL
(it drives consecutive-signal suppression). If the most recent tick is HOLD and recovery
sets `last_action = HOLD`, the next BUY would pass through suppression and double-buy
into an existing position.

Two further safeguards:

| Condition                                            | Action                                                           |
| ---------------------------------------------------- | ---------------------------------------------------------------- |
| No previous tick                                     | Default `last_action = SELL` — first run                         |
| Latest directional tick's order is FAILED            | Reverse the action (the position change never actually happened) |
| Latest directional tick's order is FILLED / no order | Use the tick's signal as-is                                      |

## Interval Flow

Each `execute_interval()` is one decision cycle:

1. Early-return if `_shutting_down` is set.
2. **Reconcile** outstanding PLACED orders (see below).
3. **Fetch OHLC** — the latest _closed_ candle. If this fails, log and return; no tick is
   persisted (`bot_ticks.price` is non-nullable).
4. Save `previous_action = strategy.last_action`, then call
   `strategy.generate_signal(ohlc)`.
5. If signal is BUY/SELL: fetch balances, calculate volume via the position sizer,
   submit the order to Kraken, **immediately persist** a partial `BotOrder` with
   `status=PLACED`, then poll Kraken (`_confirm_order()`) up to 3 times to settle it.
6. Re-fetch balances **after** the order — the tick records the post-trade portfolio state.
7. Persist the tick (price, signal, balances, optional `error`).
8. If an order was placed, link it to the tick via `bot_order_repo.update(replace(order, tick_id=tick.id))`.

Errors during signal/order flow are caught: the tick is persisted with `error` set so
nothing is lost. If the failure happens **before** the order is persisted, `last_action`
is rolled back to `previous_action` and `signal` becomes HOLD; if it happens **after**,
the order's actual side is recorded as the tick signal so recovery still reads the right
state.

## Order Lifecycle

Orders move through three states. The lifecycle is split between in-interval confirmation
and per-interval reconciliation so a transient Kraken delay never leaves an order in
limbo:

```
            ┌── _confirm_order (3× retry, 1s apart) ──┐
PLACED  ────┼── reconciled at next execute_interval ──┼──►  FILLED  (Kraken: closed)
            │                                         │
            └─────────────────────────────────────────┴──►  FAILED  (Kraken: canceled / expired)
```

| Field                  | Set on placement         | Set on settle             |
| ---------------------- | ------------------------ | ------------------------- |
| `exchange_order_id`    | extracted from `txid[0]` | —                         |
| `status`               | `PLACED`                 | `FILLED` or `FAILED`      |
| `placed_at`            | `datetime.now(utc)`      | —                         |
| `filled_at`            | `None`                   | `datetime.now(utc)`       |
| `price` `volume` `fee` | `None`                   | from `QueryOrderResult`   |
| `tick_id`              | `None`                   | linked after tick persist |

- `BotOrder` is a frozen dataclass; updates use `dataclasses.replace()` and the
  `bot_order_repo.update()` method.
- `_reconcile_placed_orders()` queries every PLACED order for this bot in one call —
  Kraken's `QueryOrders` accepts multiple txids per request, so N PLACED orders cost one
  API call.
- If a reconciled order is FAILED **and** `strategy.last_action` still matches its side,
  `last_action` is flipped to the opposite — the position change never happened.
- The naming `exchange_order_id` (domain) vs `txid` (connector) is intentional. See the
  decision log entry for the full rationale.

## Position Sizing

Volume calculation is delegated to a `PositionSizer`:

```python
class PositionSizer(ABC):
    def calculate_volume(self, signal: Signal, balances: PairBalances) -> Decimal: ...
```

The default implementation is `AllInPositionSizer`: BUY → full quote balance,
SELL → full base balance. `PairBalances` is a frozen dataclass that bundles
`symbol_base`, `symbol_quote`, `balance_base`, `balance_quote` — built once per interval
by `_fetch_balances()` so symbol lookups never travel beyond the executor.

Volume units are asymmetric (BUY in quote currency, SELL in base currency) to match
`AddOrderConnector.place()` which uses the Kraken `viqc` flag for buys.

This abstraction unblocks future sizers (Kelly, volatility-scaled, partial fills) without
changes to `TradeExecutor`. **Note:** `AllInPositionSizer` assumes exclusive access to the
pair's balance, so today the constraint is **one bot per currency pair**.

## Scheduling

```python
scheduler.add_job(
    executor.execute_interval, 'cron',
    **interval_to_cron(bot.interval),  # e.g. minute='*/5'
    second='5',                        # 5s offset for Kraken data lag
    jitter=3,                          # stagger multi-bot calls by ±3s
    misfire_grace_time=1,              # discard if >1s late
    max_instances=1,                   # never overlap intervals for one bot
)
```

| Setting                | Why                                                                                                                                                                                     |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `BlockingScheduler`    | Single-purpose script; blocks the main thread; integrates cleanly with signal handlers via `shutdown(wait=True)`.                                                                       |
| `CronTrigger`          | Wall-clock alignment (fires at `:00`, `:05`, …) — `IntervalTrigger` would drift relative to candle close.                                                                               |
| `second='5'` offset    | Kraken's most recent candle takes a second or two to propagate; firing at `:05` avoids racing it.                                                                                       |
| `jitter=3`             | Prevents N bots from hitting Kraken at exactly the same instant.                                                                                                                        |
| `misfire_grace_time=1` | If an interval runs long, **skip** the next one rather than queue it. Critical for trading safety. APScheduler 3.x treats `0` as infinite — `1` is the correct "discard if late" value. |
| `max_instances=1`      | Belt-and-braces: one `execute_interval` per bot at a time.                                                                                                                              |

## Shutdown

The signal handler in `start_scalping.py` runs the same sequence on SIGTERM and SIGINT:

1. `executor.request_shutdown()` for each executor — sets `_shutting_down = True`. Any
   currently-running `execute_interval()` finishes; subsequent firings return immediately.
2. `scheduler.shutdown(wait=True)` — blocks until the running jobs complete (including
   their post-order `_confirm_order` retry loop).
3. `executor.shutdown()` for each executor — best-effort: marks the `BotRun` as
   `completed_at = now()`. Failures are logged but do not block process exit.

No additional reconciliation runs in `shutdown()`. Any order still PLACED after the
drain belongs to the next process to resolve, via the same `get_placed_by_bot_id()` query
used during crash recovery.

## Dry Run Mode

Activated via `--dry-run` (or `DRY_RUN=true` in the container), dry run mode passes
`validate=True` to `AddOrderConnector.place()`. Kraken validates the order (pair, volume,
balance) without executing it. In this mode the executor:

- Logs a `[DRY RUN]` line per interval with signal, price, and balances.
- **Does not persist** any ticks or orders. Persisting them would corrupt
  `recover_state()` when switching to live — the bot would think it already holds a
  position it never bought.
- Skips the QueryOrders confirmation loop entirely (no `txid` exists to query).

Zero additional API cost — Kraken's validate path is free.

## Logging

`TradeExecutor` constructs a `BotLoggerAdapter` that prefixes every line with the bot id:

```
[btc_1m_001] Signal generated: signal=buy, price=…
```

The application log level is set via the `LOG_LEVEL` env var (default `INFO`). Set
`LOG_LEVEL=DEBUG` to surface routine HOLD intervals and the "no placed orders to
reconcile" message.

## Reading the Code

| Topic               | File                                            |
| ------------------- | ----------------------------------------------- |
| Executor            | `scalper/trade_executor/trade_executor.py`      |
| Position sizing     | `scalper/trade_executor/position_sizer.py`      |
| Scheduler / signals | `scalper/scripts/start_scalping.py`             |
| Bot registration    | `scalper/scripts/register_bot.py`               |
| `BotOrder` model    | `scalper/data_system/models/bot_order_model.py` |
| Schema              | `scalper/data_system/schema.sql`                |
