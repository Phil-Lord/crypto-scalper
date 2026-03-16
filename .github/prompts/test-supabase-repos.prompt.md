---
agent: agent
description: "Manually test the add, get, and update paths for the four live-trading Supabase repos and models, ensuring correct type serialisation, FK constraints, and error handling."
---

# Test Supabase Repos

Test the **add**, **get**, and **update** paths for the four live-trading Supabase repositories.

## ⚠️ Important: Scope Restriction

**Only touch the following four Supabase tables:**

| Table        | Purpose               |
|--------------|-----------------------|
| `bots`       | Live trading bots     |
| `bot_runs`   | Individual bot runs   |
| `bot_ticks`  | Tick data per run     |
| `bot_orders` | Orders placed per run |

**Do NOT read from, write to, or modify any other tables or repos** — in particular `trades` and `generalisation_evaluation`, which contain large volumes of local backtesting data that must be left completely untouched.

## Setup

Reference [query_supabase.py](../../scalper/scripts/query_supabase.py) to understand how the repos and models are constructed. However, **do not run `query_supabase.py` directly** — it is an interactive CLI tool that requires manual input and cannot be used programmatically. Instead, write your own Python script(s) to perform the tests.

The real Supabase tables have not been used for live trading yet, so it is safe to insert test data into the four tables above.

## Insertion Order

The tables have foreign key constraints. You **must** insert in this order or FK violations will occur:

1. `bots` — no dependencies
2. `bot_runs` — requires a `bot_id` → `bots`
3. `bot_ticks` — requires `bot_id` → `bots` and `run_id` → `bot_runs`
4. `bot_orders` — requires `bot_id` → `bots`, `run_id` → `bot_runs`, and optionally `tick_id` → `bot_ticks`

Use a consistent test prefix (e.g. `bot_id = 'test_btc_1m_001'`) so test data is easy to identify and clean up.

## Get Method Signatures

The `get` methods are **not uniform** across repos — note the differences:

| Repo                        | Method                                       | Returns            |
|-----------------------------|----------------------------------------------|--------------------|
| `SupabaseBotRepository`     | `get(id: str)`                               | `Bot \| None`      |
| `SupabaseBotRunRepository`  | `get(id: UUID)`                              | `BotRun \| None`   |
| `SupabaseBotRunRepository`  | `complete(id: UUID, completed_at: datetime)` | `BotRun \| None`   |
| `SupabaseBotTickRepository` | `get_by_bot_id(bot_id: str)`                 | `list[BotTick]`    |
| `SupabaseBotOrderRepository`| `get_by_bot_id(bot_id: str)`                 | `list[BotOrder]`   |
| `SupabaseBotOrderRepository`| `get_placed_by_bot_id(bot_id: str)`          | `list[BotOrder]`   |
| `SupabaseBotOrderRepository`| `update(bot_order: BotOrder)`                | `BotOrder`         |

Ticks are returned ordered by `timestamp DESC`; orders (both get methods) are returned ordered by `placed_at DESC`. `get_placed_by_bot_id` filters to `status = 'placed'` only.

## Test Scenarios

For each repo, test both the add and get paths. Cover:

### `bots`
- Add a bot with a representative `parameters` dict (nested values, multiple keys)
- Verify `get(id)` returns a `Bot` that matches exactly — including `parameters` dict and `created_at` timezone
- Add a duplicate `id` and confirm it raises an error (PK constraint)
- `get` a non-existent `id` and confirm `None` is returned

### `bot_runs`
- Add a run with `completed_at=None` (the normal open state)
- Add a run with a specific `completed_at` datetime (timezone-aware)
- Verify `get(id: UUID)` returns the correct `BotRun` — confirm `id` is a `UUID`, `completed_at` is `None` or a timezone-aware `datetime` as appropriate
- `get` a non-existent `id` and confirm `None` is returned

#### `complete`
- Insert a run with `completed_at=None`, then call `complete(id, completed_at)` with a timezone-aware UTC datetime
- Verify the returned `BotRun` has `completed_at` set exactly to the supplied datetime (timezone-aware, not naive)
- Verify `get(id)` reflects the updated state — `completed_at` is no longer `None`
- Call `complete` with a non-existent `id` and confirm `None` is returned

### `bot_ticks`
- Add a tick for each `Signal` value (`buy`, `hold`, `sell`)
- Add a tick with `error=None` and one with a non-null `error` string
- Verify that `BotTick.id` is `None` before insert and populated (int) after — the returned object should have the DB-assigned BIGSERIAL value
- Verify `get_by_bot_id` returns all inserted ticks with `Decimal` fields (`price`, `balance_base`, `balance_quote`) preserved exactly — use values realistic for Kraken trading data (e.g. `Decimal('45123.50')` for price, `Decimal('0.00012345')` for volume/fees/balances) to catch float conversion bugs without triggering known schema limits (see Known Limitations below)
- Verify `Signal` enum is correctly deserialised on the way back

### `bot_orders`
- Add an order with all optional fill fields as `None` (default `placed` status)
- Add a fully-populated order (`filled` status, all Decimal fields set, `filled_at` datetime set)
- Verify `get_by_bot_id` returns all inserted orders with correct `Side`, `OrderStatus`, `Decimal` precision, and datetime timezone
- Verify `tick_id` is `None` and populated correctly in each case

#### `get_placed_by_bot_id`
- Insert one `placed` order and one `filled` order for the same `bot_id`
- Verify `get_placed_by_bot_id` returns **only** the `placed` order, not the `filled` one
- Verify the returned list is empty when no `placed` orders exist for a given `bot_id`

#### `update`
- Insert a `placed` order, then call `update` to transition it to `filled` — set `filled_at`, `price`, `volume`, `fee`, and `status = OrderStatus.FILLED`
- Verify the returned `BotOrder` from `update` reflects all updated values exactly (including `Decimal` precision, `OrderStatus` enum, and timezone-aware `filled_at`)
- Verify `get_by_bot_id` reflects the updated state (the order appears as `filled`)
- Verify `get_placed_by_bot_id` no longer returns the order after it has been updated to `filled`

## Type Serialisation Round-Trips

The repos serialise types for Supabase and deserialise them on return. Verify each conversion survives the round-trip without loss:

| Type          | Verify                                                                                      |
|---------------|---------------------------------------------------------------------------------------------|
| `datetime`    | Timezone-aware UTC preserved (not stripped to naive)                                        |
| `Decimal`     | Precision preserved using realistic values (1–8 dp) — see Known Limitations for constraints |
| `UUID`        | Deserialised back to `UUID`, not left as a string                                           |
| `Signal`      | Deserialised back to `Signal` enum, not a plain string                                      |
| `Side`        | Deserialised back to `Side` enum                                                            |
| `OrderStatus` | Deserialised back to `OrderStatus` enum                                                     |
| `dict`        | JSONB round-trip preserves structure exactly (no type coercion)                             |

## Cleanup

After all tests, **delete the test data** to keep the tables clean. There are no delete methods on the repos, so use the raw Supabase client directly:

```python
client.table('bot_orders').delete().eq('bot_id', 'test_btc_1m_001').execute()
client.table('bot_ticks').delete().eq('bot_id', 'test_btc_1m_001').execute()
client.table('bot_runs').delete().eq('bot_id', 'test_btc_1m_001').execute()
client.table('bots').delete().eq('id', 'test_btc_1m_001').execute()
```

Delete in reverse insertion order to respect FK constraints.

## Known Limitations

Two Decimal precision behaviours are **expected and not bugs** — do not flag them as failures:

1. **Schema truncation (`DECIMAL(32, 12)`)** — PostgreSQL silently truncates values with more than 12 fractional digits. Kraken data never exceeds 8 dp in practice, so this is harmless. Do not use test values with >12 dp.

2. **PostgREST float64 rounding** — PostgREST serialises `NUMERIC` columns as JSON `number` (float64), which can lose the 12th decimal place (max error: `0.000000000001`). This is irrelevant for GBP-denominated trading. If a returned `Decimal` differs from the inserted value only in the 12th decimal place, treat it as a **warning**, not a failure.

Both issues are documented in the Architecture Decision Log.

## Output

Summarise results per repo: which paths passed, which failed, and any issues found. Call out any schema mismatches, type deserialisation failures, unexpected `None` values, or constraint violations. Distinguish hard failures from known precision warnings (see Known Limitations).