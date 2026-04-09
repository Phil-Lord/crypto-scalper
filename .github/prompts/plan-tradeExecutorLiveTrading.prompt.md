# Plan: Trade Executor + Live Trading on Fly.io

**TL;DR:**
- Rewrite the trade executor module as an always-on process that:
  1. loads bot config from Supabase
  2. warms up strategy indicators from OHLC history (using a `warmup_candles` property on each strategy)
  3. recovers state from the latest persisted tick — called after warm-up so the DB value overrides whatever warm-up produced
  4. runs a BlockingScheduler with CronTrigger per bot interval (with jitter, fixed delay, misfire protection)
  5. persists every tick and order to Supabase.
- Build a `QueryOrdersConnector` in the exchange connector to fetch fill details from Kraken after order placement, with a retry loop and per-interval reconciliation of outstanding orders.
- Extend `BotOrder` with `status`/`exchange_order_id`/`placed_at`/`filled_at` fields for order safety — persist immediately after placement, update on fill.
- Add an injectable `PositionSizer` abstraction for volume calculation.
- Deploy as a Docker container on Fly.io with `fly deploy`. The core executor is platform-agnostic — Fly.io specifics are confined to the Dockerfile, `fly.toml`, `entrypoint.sh`, and the entry-point script.

**Key decisions reflected:**
- Platform: Fly.io (~$2/month), CronTrigger + jitter + 5s delay
- Bot config: DB-registered (looked up from Supabase `bots` table by `bot_id`)
- Warm-up: Skip recording ticks until indicators are ready; warn if insufficient candles; requirement derived from `Strategy.warmup_candles` property
- Order fills: Build `QueryOrdersConnector` to retrieve actual execution details; retry 3× in-interval, reconcile outstanding PLACED orders every interval
- Order safety: Extend `BotOrder` with `status`/`exchange_order_id`/`placed_at`/`filled_at`; persist immediately after placement, update on fill
- State recovery: Query latest *directional* tick (BUY/SELL, not HOLD) on startup to restore `strategy.last_action`
- Volume: Injectable `PositionSizer` with `AllInPositionSizer` default
- No `IntervalContext`: Transformation logic lives in private `TradeExecutor` methods
- Error ticks: Skip on OHLC failure; persist with error field when price data available
- Graceful shutdown: `BlockingScheduler.shutdown(wait=True)` + `_shutting_down` flag; `misfire_grace_time=0` and `max_instances=1` per job
- Dry run mode: `--dry-run` flag passes `validate=True` to Kraken (no real orders); log-only, no ticks or orders persisted
- Health monitoring: Use `bot_ticks` timestamps — no schema changes needed
- Logging: Text format for now; switch to JSON when a log sink is added

## Phase 1: Exchange Connector — QueryOrders Support

1. **Add `QueryOrdersService`** at `exchange_connector/services/query_orders_service.py`. Inherits `KrakenService`. Calls Kraken's `POST /0/private/QueryOrders` endpoint with `txid` param. Returns raw dict of order details keyed by txid. Kraken response includes `price` (average executed price), `vol_exec` (volume executed), and `fee`.

2. **Add `QueryOrderResult` domain model** at `exchange_connector/models/query_order_result.py`. Frozen dataclass with fields: `txid: str`, `price: Decimal`, `volume: Decimal`, `fee: Decimal`, `status: str`. This is the typed representation of a filled order's execution details. `price`, `volume`, and `fee` should not be nullable, 

3. **Add `QueryOrdersConnector`** at `exchange_connector/connectors/query_orders_connector.py`. Inherits `FetchConnector`. Method: `fetch(txids: list[str]) -> list[QueryOrderResult]`. Delegates to `QueryOrdersService`, transforms raw response into `QueryOrderResult` domain objects by extracting `price`, `vol_exec`, and `fee` from each order entry.

4. **Export new symbols** from `exchange_connector/__init__.py` — add `QueryOrdersConnector` and `QueryOrderResult`. Also export from `exchange_connector/models/__init__.py` and `exchange_connector/connectors/__init__.py`.

5. **Unit tests** for `QueryOrdersService` and `QueryOrdersConnector` in `tests/unit/exchange_connector/`. Follow existing patterns (e.g., `TestAddOrderConnector`). Test happy path, error parsing, multi-txid response, and `_to_domain` conversion. Register markers `query_orders_service` and `query_orders_connector` in `pytest.ini`.

## Phase 2: Data System — Model + Repository Extensions

6. **Extend `BotOrder` model** at `data_system/models/bot_order_model.py`:
    - Add `OrderStatus(str, Enum)`: `PLACED = 'placed'`, `FILLED = 'filled'`, `FAILED = 'failed'`
    - Add `exchange_order_id: str` field — the Kraken order ID (what Kraken calls `txid`); named `exchange_order_id` in the domain layer for clarity (see naming decision in Decisions section)
    - Add `status: OrderStatus` field (default `PLACED`)
    - Make `price`, `volume`, `fee` optional: `Decimal | None = None`
    - Make `tick_id` optional: `int | None = None` (may not have tick ID at placement time)
    - Add `placed_at: datetime` field (default `datetime.now(utc)`) — always records when the order was submitted, independent of tick persistence
    - Rename `executed_at` → `filled_at: datetime | None = None` — set when fill details arrive from QueryOrders

    **Note:** `BotOrder` remains `frozen=True`. Updates (e.g., setting fill details or `tick_id` after persistence) use `dataclasses.replace()` to create a new instance, which is then passed to `bot_order_repo.update()`. This maintains immutability consistency with all other domain models.

7. **Update `bot_orders` schema** in `data_system/schema.sql`:
    - Add `exchange_order_id TEXT NOT NULL` — stores the Kraken order ID (what Kraken calls `txid`)
    - Add `status TEXT NOT NULL DEFAULT 'placed'` with `CHECK (status IN ('placed', 'filled', 'failed'))`
    - Add `placed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
    - Make `price`, `volume`, `fee` nullable: `DECIMAL(32, 12)` (remove NOT NULL)
    - Make `tick_id` nullable (already is — `REFERENCES` without NOT NULL)
    - Rename `executed_at` → `filled_at`: make nullable, remove `NOT NULL` and `DEFAULT NOW()`
    - **No migration needed** — no production data exists yet. Recreate the table from the updated schema.

8. **Add `update()` method to `BotOrderRepository`** at `data_system/repositories/bot_order/bot_order_repository.py`. Signature: `update(self, bot_order: BotOrder) -> BotOrder`. Updates an existing order record (used to fill in price/volume/fee/filled_at after QueryOrders succeeds).

9. **Implement `update()` in `SupabaseBotOrderRepository`** at `data_system/repositories/bot_order/supabase_bot_order_repository.py`.

10. **Add `get_placed_by_bot_id()` to `BotOrderRepository`** at `data_system/repositories/bot_order/bot_order_repository.py`. Signature: `get_placed_by_bot_id(self, bot_id: str) -> list[BotOrder]`. Returns all orders with `status='placed'` for a given bot. Used by `execute_interval` to reconcile outstanding orders every interval.

11. **Implement `get_placed_by_bot_id()` in `SupabaseBotOrderRepository`**. Query with `.eq('bot_id', bot_id).eq('status', 'placed').execute()`.

11a. **Add `get_by_tick_id()` to `BotOrderRepository`** at `data_system/repositories/bot_order/bot_order_repository.py`. Signature: `get_by_tick_id(self, tick_id: int) -> BotOrder | None`. Returns the order associated with a given tick ID, or `None` if not found. Used by `recover_state()` to check whether the order recorded at the most recent directional tick ended up FAILED — without fetching all orders for the bot.

11b. **Implement `get_by_tick_id()` in `SupabaseBotOrderRepository`**. Query with `.eq('tick_id', tick_id).execute()`. Returns the first result or `None`.

12. **Add `complete()` method to `BotRunRepository`** at `data_system/repositories/bot_run/bot_run_repository.py`. Signature: `complete(self, id: UUID, completed_at: datetime) -> BotRun`. Abstract method to mark a run as finished by setting `completed_at`.

13. **Implement `complete()` in `SupabaseBotRunRepository`** at `data_system/repositories/bot_run/supabase_bot_run_repository.py`. Uses `client.table('bot_runs').update({'completed_at': completed_at.isoformat()}).eq('id', str(id)).execute()`, then returns the deserialised `BotRun`.

14. **Add `get_latest_action_by_bot_id()` to `BotTickRepository`**. Signature: `get_latest_action_by_bot_id(self, bot_id: str) -> BotTick | None`. Returns the most recent tick with `signal IN ('buy', 'sell')` for a bot — i.e., the last *directional* action, excluding HOLD ticks. Used exclusively by `recover_state()` to correctly restore `strategy.last_action`, which is only ever `BUY` or `SELL` (never `HOLD`). Without this filter, recovering from a HOLD tick would corrupt the consecutive-signal suppression logic — e.g., if the bot bought, then held for 20 intervals (latest tick signal = HOLD), crash-recovery would set `last_action = HOLD`, causing the next BUY signal to pass through suppression unchecked → double buy into an existing position.

15. **Implement `get_latest_action_by_bot_id()` in `SupabaseBotTickRepository`**. Query with `.eq('bot_id', bot_id).in_('signal', ['buy', 'sell']).order('timestamp', desc=True).limit(1)`.

16. **Unit tests** for all new/modified repository methods and the updated `BotOrder` model. Follow existing patterns in `tests/unit/data_system/`.

17. **Update `data_system` exports** — export `OrderStatus` from `data_system/models/__init__.py` and `data_system/__init__.py`.

## Phase 3: Position Sizing

**Precursor — already done:** Added `PairSymbols` frozen dataclass (`base: str`, `quote: str`) to `utils/pair_config.py`. Updated `get_kraken_pair_symbols()` to return `PairSymbols` instead of `dict[str, str]`. Exported from `utils/__init__.py`. Updated existing callers (`scripts/add_order.py`, `tests/unit/utils/test_pair_config.py`) to attribute access (`.base`, `.quote`).

18. **Add `PositionSizer` abstract base class** at `trade_executor/position_sizer.py`. Also define a `PairBalances` frozen dataclass in the same file with fields `symbol_base: str`, `symbol_quote: str`, `balance_base: Decimal`, and `balance_quote: Decimal` — merges the pair symbol info from `get_kraken_pair_symbols()` with the actual balance amounts into a single typed object. `PositionSizer` interface: `calculate_volume(self, signal: Signal, balances: PairBalances) -> Decimal`. ABC with a single abstract method.

19. **Add `AllInPositionSizer`** in the same file. Implements `calculate_volume()`: buy → `balances.balance_quote` (full quote balance), sell → `balances.balance_base` (full base balance). This replicates current behaviour.

20. **Unit tests** for `AllInPositionSizer` at `tests/unit/trade_executor/test_position_sizer.py`.

## Phase 4: Strategy Manager — Warm-up Property

21. **Add abstract `warmup_candles` property to `Strategy`** at `strategy_manager/strategies/base_strategy.py`. Signature: `@property @abstractmethod def warmup_candles(self) -> int`. Each strategy must declare how many candles it needs for indicator convergence.

22. **Implement `warmup_candles` on `PrecisionTrendStrategy`** — returns `3 * max(self.config.short_ema, self.config.long_ema, self.config.rsi_window, self.config.adx_window, self.config.atr_window)`. The 3× multiplier is the standard EMA convergence heuristic — after 3× the window length, the seed value's contribution to the EMA carries ~5% weight ($e^{-3} \approx 0.05$). The actual output error depends on how far the seed is from the true EMA, so for a well-chosen seed (e.g., SMA of the first N values) the practical error is smaller. Changing indicator windows in `utils/strategy_configs.py` automatically adjusts the warm-up requirement — no strategy code changes needed.

23. **Implement `warmup_candles` on `SmaStrategy`** — returns `self.config.long_window + 1`. SMA needs exactly N candles plus 1 for crossover detection.

24. **Unit tests** for `warmup_candles` on both strategies. Verify the property returns the expected value for the default config, and that changing config parameters changes the result.

## Phase 5: Trade Executor — Core Rewrite

25. **Delete** the current `trade_executor/config.py` and `trade_executor/handler.py`. These are Lambda artefacts being replaced.

26. **Delete `IntervalContext`** at `trade_executor/interval_context.py`. Transformation logic moves to private `TradeExecutor` methods (`_fetch_ohlc()`, `_fetch_balances()`). Also **drop `TickerConnector`** from the executor — the current executor uses it to get a `float` price, but `Strategy.generate_signal()` expects a `pd.Series` with `open`/`high`/`low`/`close` keys. `OhlcConnector` provides all required fields in a single call, replacing `TickerConnector` entirely.

27. **Rewrite `TradeExecutor`** at `trade_executor/trade_executor.py`. Complete redesign:

    - **Constructor** takes dependency-injected components:
      - `bot: Bot` — configuration from Supabase
      - `strategy: Strategy` — created from `bot.strategy_name` + `bot.parameters` via `create_strategy()`
      - `position_sizer: PositionSizer` — injectable, default `AllInPositionSizer`
      - `dry_run: bool = False` — when `True`, orders are validated but not executed
      - `bot_run_repo: BotRunRepository`
      - `bot_tick_repo: BotTickRepository`
      - `bot_order_repo: BotOrderRepository`
      - Connectors: `OhlcConnector`, `BalanceConnector`, `AddOrderConnector`, `QueryOrdersConnector`
    - Stores `self.pair_symbols: PairSymbols` from `get_kraken_pair_symbols(bot.pair)` — used internally by `_fetch_balances()` to look up base and quote asset symbols in Kraken's balance response; not passed downstream
    - Creates `run: BotRun` on construction and persists it via `bot_run_repo.add()`
    - Has `self._shutting_down = False` flag for graceful drain
    - **`request_shutdown(self) -> None`**: Sets `self._shutting_down = True`. Called by the signal handler in `start_scalping.py` — keeps mutation of internal state behind a public method rather than reaching into a private attribute from outside the class.
    - Uses a `logging.LoggerAdapter` with `{'bot_id': bot.id}` extra context — all log calls automatically include bot ID, critical for debugging multi-bot processes
    - **`recover_state(self) -> None`**: Queries latest directional tick via `bot_tick_repo.get_latest_action_by_bot_id(bot.id)` — returns only BUY/SELL ticks, never HOLD. If found, sets `strategy.last_action` from tick's signal. Logs recovery details or 'first run' if no tick exists.
    - **`_fetch_ohlc(self) -> pd.Series`**: Private method. Fetches latest OHLC via `OhlcConnector` using `since = int(time.time()) - interval * 60 * 2`. Using 2 intervals back rather than 1 is required: Kraken returns candles whose start timestamp >= since, plus always appends the forming candle. With only 1 interval back, the previous closed candle's start falls before since and is excluded, leaving only the forming candle duplicated at `[-2]` and `[-1]`. Two intervals back guarantees a distinct completed candle at `[-2]`. Extracts `candles[-2]` (an `OhlcCandle`), returns as `pd.Series` with keys `open`, `high`, `low`, `close` matching what `Strategy.generate_signal()` expects. Used by `execute_interval()` for single-candle fetches.
    - **`_fetch_ohlc_history(self) -> list[pd.Series]`**: Private method. Fetches historical OHLC candles via `OhlcConnector` using a `since` timestamp derived from `bot.interval * (min(strategy.warmup_candles, 720) + 1)` — the extra interval compensates for `since` landing mid-interval: Kraken's `start >= since` filter excludes the oldest candle whose minute boundary falls just before `since`. Returns `candles[:-1]` as a list of `pd.Series` — the forming (not-yet-committed) candle is always the last element returned by Kraken and must be excluded, for the same reason as `_fetch_ohlc()`. If `warmup_candles > 720`, logs a warning before capping. Used exclusively by `warm_up()`. Separate from `_fetch_ohlc()` because the return type (`list[pd.Series]` vs `pd.Series`) and `since` calculation logic are fundamentally different.
        - **Kraken 720-candle hard limit**: Kraken's OHLC endpoint returns at most 720 of the most recent candles. Older data cannot be retrieved regardless of the `since` value — pagination is not possible. Request `min(warmup_candles, 720)` candles. If `warmup_candles > 720` (e.g., an Optuna-optimised `SmaStrategy` with `long_window > 719`), the warm-up will be partial — the existing `warm_up()` validation already handles this by logging a warning and continuing. Solving warm-up beyond 720 candles (e.g., from stored local trades) is deferred to a future task; it does not affect `PrecisionTrendStrategy` whose maximum warm-up requirement is 237 candles.
    - **`_fetch_balances(self) -> PairBalances`**: Private method. Fetches balances via `BalanceConnector`, looks up `self.pair_symbols.base` and `self.pair_symbols.quote` in Kraken's response, converts string values to `Decimal`, handles missing keys (zero balance). Returns a `PairBalances(symbol_base=..., symbol_quote=..., balance_base=..., balance_quote=...)` frozen dataclass instance — all balance and symbol information for the pair in one object.
    - **`warm_up(self) -> None`**: Fetches historical OHLC candles via `self._fetch_ohlc_history()`, feeds them sequentially through `strategy.generate_signal()` to warm up indicators. Logs progress but does **not** persist ticks during warm-up. Logs a completion message with the count of candles processed.
        - **Warm-up validation**: After fetching, check that candle count meets `self.strategy.warmup_candles`. If insufficient (e.g., new trading pair), log a warning that signals may be unreliable for the first N intervals. Bot starts anyway (warn and continue).
    - **`_reconcile_placed_orders(self) -> None`**: Queries outstanding PLACED orders via `bot_order_repo.get_placed_by_bot_id(bot.id)`. If none, returns immediately. Otherwise collects all `exchange_order_id` values into a list and calls `QueryOrdersConnector.fetch(exchange_order_ids)` once — Kraken's `QueryOrders` endpoint accepts multiple order IDs in one request. Iterates the results: if Kraken reports `closed` → update to FILLED with fill details and `filled_at`; if `cancelled` → update to FAILED **and roll back `strategy.last_action` to the opposite side (BUY→SELL, SELL→BUY) if `last_action` currently matches the failed order's side** — the order never executed so the strategy's assumed position must be unwound; if still `open` → leave as PLACED (will retry next interval). Logs each resolution.
    - **`execute_interval(self) -> None`**: One decision cycle:
      1. Check `self._shutting_down` — if True, return immediately (graceful drain)
      2. Reconcile outstanding PLACED orders via `self._reconcile_placed_orders()`
      3. Fetch latest closed OHLC candle via `self._fetch_ohlc()`. If this fails, log error and return (no tick persisted — required fields are non-nullable)
      4. Call `strategy.generate_signal(ohlc)` → extract post-suppression `Signal` from result dict
      5. If signal is `BUY` or `SELL`:
          - Fetch balances via `self._fetch_balances()` (before order, to calculate volume)
          - Calculate volume via `position_sizer.calculate_volume(signal, balances)` — `balances` is a `PairBalances` instance containing both amounts and symbol names
          - Place order via `AddOrderConnector.place(pair, signal, volume, validate=self.dry_run)` → get `AddOrderResult`
          - **If `self.dry_run`:** Log the validated order description from `AddOrderResult`. Skip order persistence, QueryOrders, and post-trade balance fetch — no real order was placed.
          - **If live (not dry run):**
              - Extract `exchange_order_id = order_result.txid[0]` (guard for `None` — should not happen outside `validate=True` mode; raise `ValueError` if it is)
              - **Immediately persist** partial `BotOrder` with `exchange_order_id`, status=`PLACED`, fill fields=`None`, `filled_at=None`
              - **Retry QueryOrders up to 3 times** (1s delay between attempts) via `_confirm_order()`. Check for Kraken's `status='closed'` (fully filled). `_confirm_order()` returns the updated `BotOrder` in all cases (FILLED, FAILED, or still PLACED after retries) so `execute_interval` always holds the current state when linking the tick.
                  - On fill success (status `closed`): call `mark_filled()` → returns updated `BotOrder` with status=`FILLED`
                  - On still open after 3 attempts: leave as `PLACED`, log info — will be reconciled at the start of the next interval; return original `BotOrder`
                  - On `cancelled` status: call `mark_failed()` → returns updated `BotOrder` with status=`FAILED`
              - Reassign `placed_order` to the return value of `_confirm_order()` to ensure the correct status is used when linking the tick
              - **If `placed_order.status == OrderStatus.FAILED` after `_confirm_order()`**: restore `strategy.last_action = previous_action`, set `signal = Signal.HOLD`, set `tick_error` — the order did not execute; recording a BUY/SELL tick or leaving `last_action` advanced would corrupt consecutive-signal suppression
              - Fetch balances again after order flow to get post-trade balances for the tick record
      6. If signal is `HOLD` (or BUY/SELL without entering the order branch): `balances` is still `None` — fetch via `self._fetch_balances()`
      7. **If `self.dry_run`:** Log tick summary (price, signal, balances) and return — no persistence. This prevents dry run ticks from polluting `bot_ticks` and corrupting `_recover_state()` when switching to live mode.
      8. Construct `BotTick` with `bot_id`, `run_id`, `timestamp`, `price` (from OHLC, cast to `Decimal`), `signal` (post-suppression), `balance_base`, `balance_quote`, `error` — balances always reflect the bot's position **after** acting on the signal
      9. Persist tick via `bot_tick_repo.add()` → get back tick with DB-generated `id`
      10. If order was placed: update `BotOrder.tick_id` via `bot_order_repo.update(replace(placed_order, tick_id=tick.id))` — `placed_order` holds the post-`_confirm_order` state (FILLED/FAILED/PLACED), so the update preserves the correct status.
      11. Log results
    - **Error handling**: The signal/order block (steps 4–6) is wrapped in a single try/except. Before calling `generate_signal()`, save `previous_action = self.strategy.last_action`. If OHLC fetch fails → log error, return (no tick — can't construct BotTick without price). If strategy or order placement fails → catch the exception, set `tick_error = str(e)`, **if `placed_order is None` restore `self.strategy.last_action = previous_action`** (no order was persisted before the failure, so `generate_signal()`'s mutation of `last_action` must be undone), fall back to `signal = Signal.HOLD`, attempt to fetch balances (return if that also fails), then persist tick with `error` field set. On fatal errors (Supabase unreachable): log and let the process crash (Fly.io auto-restarts).
    - **`shutdown(self) -> None`**: Marks the run as completed via `bot_run_repo.complete(self.run.id, datetime.now(timezone.utc))`. Wraps the DB call in try/except (best-effort cleanup — a Supabase network error should not prevent the process from exiting cleanly). Does **not** call `_reconcile_placed_orders()`: by the time `shutdown()` is called, `scheduler.shutdown(wait=True)` has already blocked until the current interval completed (including its own reconciliation step), and `_shutting_down = True` prevents any new interval from starting. Any order that still has `status='placed'` after that interval's 3-retry window will be picked up by the next run's `get_placed_by_bot_id()` query at the start of its first `execute_interval()` — the same recovery path that handles crash restarts.
    - **No `load_env()`** or `logging.basicConfig()` — these stay in the entry-point script only.
    - **No internal connector instantiation** — all injected via constructor.

28. **Update `trade_executor/__init__.py`**. Export `TradeExecutor`, `PositionSizer`, `AllInPositionSizer`, `PairBalances`.

## Phase 6: Scheduler + Entry Point

29. **Add `apscheduler` to `pyproject.toml`** by running `uv add "apscheduler>=3.10,<4.0"`. The `<4.0` upper bound is necessary — version 4.x is a complete async rewrite that removed `BlockingScheduler` and `CronTrigger` entirely; without the pin, uv would resolve 4.x and the script would not run. (`supabase` is already present in `pyproject.toml` from the uv migration.)

30. **Rewrite `start_scalping.py`** at `scripts/start_scalping.py`. New flow:
    - `load_env()` + `logging.basicConfig()` (entry-point responsibilities)
    - Click CLI: `--bot-id` (required, `multiple=True`), `--dry-run` (flag, default `False`). Example: `--bot-id btc_1m_001 --bot-id eth_5m_v2 --dry-run`
    - For each `bot_id`:
      1. Look up `Bot` from Supabase via `SupabaseBotRepository.get(bot_id)` — fail if not found
      2. Create strategy via `create_strategy(bot.strategy_name, bot.parameters)` — note: `bot.strategy_version` is metadata for auditing/debugging only, not used by `create_strategy()`
      3. Create `AllInPositionSizer()` (or future: select sizer from config)
      4. Instantiate `TradeExecutor` with all dependencies (repositories, connectors, strategy, position sizer, bot, `dry_run=dry_run`)
      5. Call `executor.warm_up()` — feeds historical candles to converge indicators; blocks until complete
      6. Call `executor.recover_state()` — restore `last_action` from latest directional (BUY/SELL) tick; must run **after** `warm_up()` so the DB-persisted position overrides whatever `last_action` warm-up produced
      7. Schedule `executor.execute_interval` with APScheduler **`BlockingScheduler`** using **`CronTrigger`** aligned to wall-clock + **5-second offset** + **`jitter=3`** + **`misfire_grace_time=0`** + **`max_instances=1`** (e.g., `CronTrigger(minute='*', second=5)` for 1-min interval, `CronTrigger(minute='*/5', second=5)` for 5-min). The 5-second offset handles Kraken data propagation delay. Jitter prevents simultaneous API calls from multiple bots. `misfire_grace_time=0` skips misfired executions rather than stacking them. `max_instances=1` ensures only one `execute_interval` runs per bot at a time.
    - Register signal handlers for `SIGTERM`/`SIGINT`:
      1. Call `executor.request_shutdown()` on each executor (sets `_shutting_down = True`, prevents new intervals from doing work)
      2. Call `scheduler.shutdown(wait=True)` — blocks until any currently-running jobs finish
      3. Call `executor.shutdown()` on each executor (marks runs complete)
      4. Exit
    - Start the **`BlockingScheduler`** — blocks the main thread

31. **Add `register_bot.py`** at `scripts/register_bot.py`. Click CLI to insert a `Bot` record into Supabase. Options: `--id`, `--pair`, `--strategy-name`, `--strategy-version`, `--interval`, `--parameters` (JSON string). This is a helper for initial bot setup — run once per bot before starting the executor. Note: `--strategy-version` is metadata for record-keeping; it is not used functionally by the executor.

## Phase 7: Deployment — Fly.io

32. **Create `Dockerfile`** at project root. Multi-stage build:
    - Base: `python:3.13-slim`
    - Copy `pyproject.toml` and `uv.lock` first, then install dependencies:
      ```dockerfile
      COPY pyproject.toml uv.lock ./
      RUN pip install uv && uv sync --frozen --no-group dev --no-group docs
      ```
      `--frozen` ensures the lockfile is used exactly (no re-resolution at build time). `--no-group dev --no-group docs` keeps test and docs tooling out of the image.
    - Copy `scalper/` source
    - Copy `entrypoint.sh`
    - `ENTRYPOINT ["./entrypoint.sh"]`

33. **Create `entrypoint.sh`** at project root. Parses comma-separated `BOT_IDS` env var into `--bot-id` flags. Validates that `BOT_IDS` is set and non-empty — exits with a clear error message if missing (`echo "Error: BOT_IDS env var is required" && exit 1`). If `DRY_RUN=true` env var is set, appends `--dry-run` to the command. Example: `BOT_IDS=btc_1m_001,eth_5m_v2` → `python -m scripts.start_scalping --bot-id btc_1m_001 --bot-id eth_5m_v2`. With `DRY_RUN=true` → appends `--dry-run`. Adding a bot requires updating the `BOT_IDS` env var and running `fly deploy` (restart is safe — warm-up replays history, `recover_state()` restores position).

34. **Create `fly.toml`** at project root. Configuration:
    - `app = 'crypto-scalper'`
    - Region: `lhr` (London — closest to Kraken EU)
    - Machine: `shared-cpu-1x`, 256MB RAM
    - No HTTP service (internal process, no ports exposed)
    - Auto-restart: `restart` policy on failure
    - `auto_stop_machines = false` — prevents Fly.io from stopping the machine when it detects no inbound HTTP traffic

35. **Create `.dockerignore`** — exclude everything not needed at runtime:
    ```
    .git/
    .github/
    .env
    .venv/
    venv/
    legacy/
    docs/
    site/
    mkdocs.yml
    pytest.ini
    *.md
    __pycache__/
    *.pyc
    scalper/local_storage/
    scalper/logs/
    scalper/tests/
    scalper/backtesting_engine/
    scalper/study_analyser/
    ```
    Only `scalper/` production modules (`data_system`, `exchange_connector`, `strategy_manager`, `trade_executor`, `utils`, `scripts`), `pyproject.toml`, `uv.lock`, and `entrypoint.sh` are copied into the image. Test code, analysis tools, local storage, docs, and secrets are excluded.

36. **Secrets management**: Kraken API keys and Supabase credentials stored as Fly.io secrets (`fly secrets set KRAKEN_TRADING_API_KEY=... KRAKEN_TRADING_API_SECRET=... SUPABASE_URL=... SUPABASE_KEY=...`). These become environment variables in the container — the existing `SupabaseConfig` metaclass and `os.getenv` patterns already handle this.

36b. **Nonce thread-safety**: `get_nonce()` in `exchange_connector/kraken_utils/kraken_auth_utils.py` has been updated to use `time.time_ns()` (nanosecond precision) rather than `int(time.time() * 1000)` (millisecond precision). Two bots hitting private Kraken endpoints in the same millisecond from APScheduler's thread pool would produce identical nonces → `EAPI:Invalid nonce`. Nanosecond precision makes collisions effectively impossible.

36c. **Supabase client thread-safety**: Each `TradeExecutor` should receive its own `SupabaseClient` instance (constructed in the entry-point script per bot). The underlying `httpx` client used by the Supabase SDK may not be thread-safe for concurrent writes from APScheduler's thread pool. One client per executor avoids shared-state issues.

## Phase 8: Tests

37. **Rewrite unit tests** for `TradeExecutor` at `tests/unit/trade_executor/test_trade_executor.py`. New tests covering:
    - `test_execute_interval_buy_persists_tick_and_order` — verify tick repo receives `BotTick` with correct fields, order repo receives `BotOrder` with `exchange_order_id` (extracted from `order_result.txid[0]`) and status=PLACED, then updated to FILLED with fill details and `filled_at` from `QueryOrdersConnector`. Verify balances fetched **after** order fill.
    - `test_execute_interval_hold_persists_tick_only` — no order placed, tick still recorded
    - `test_execute_interval_sell_persists_tick_and_order` — sell path
    - `test_execute_interval_ohlc_failure_skips_tick` — when OHLC fetch throws, no tick persisted, error logged
    - `test_execute_interval_strategy_error_persists_tick_with_error` — when strategy throws, tick is saved with `error` field
    - `test_execute_interval_query_fill_retries_three_times` — verify QueryOrders called up to 3 times with 1s delay
    - `test_execute_interval_query_fill_still_open_leaves_placed` — order still `open` after 3 attempts, status stays PLACED (not FAILED)
    - `test_execute_interval_query_fill_cancelled_marks_failed` — Kraken reports `cancelled`, status set to FAILED and `strategy.last_action` rolled back to pre-signal value
    - `test_execute_interval_last_action_rolled_back_on_pre_order_exception` — exception thrown before `placed_order` is persisted (e.g., balance fetch fails); `strategy.last_action` restored to its pre-`generate_signal` value
    - `test_execute_interval_last_action_not_rolled_back_when_order_persisted` — exception thrown after `placed_order` is persisted; `strategy.last_action` is NOT restored (order is in DB as PLACED, position did change)
    - `test_execute_interval_skipped_when_shutting_down` — verify early return when `_shutting_down` is True
    - `test_reconcile_placed_orders_resolves_filled` — verify outstanding PLACED order updated to FILLED when Kraken reports `closed`
    - `test_reconcile_placed_orders_resolves_cancelled` — verify outstanding PLACED order updated to FAILED when Kraken reports `cancelled`, and `strategy.last_action` rolled back to opposite side
    - `test_reconcile_placed_orders_leaves_open` — verify still-open orders left as PLACED
    - `test_reconcile_called_every_interval` — verify `_reconcile_placed_orders` is called at the start of each `execute_interval`
    - `test_warm_up_feeds_candles_sequentially` — verify OHLC fetched and each candle fed through `generate_signal()`, no ticks persisted
    - `test_warm_up_uses_strategy_warmup_candles` — verify the `since` param to `OhlcConnector.fetch()` is derived from `strategy.warmup_candles + 1` (the +1 guarantees a full candle count after `[:-1]` drops the forming candle)
    - `test_warm_up_caps_fetch_at_720_candles` — verify that when `strategy.warmup_candles > 720`, since is derived from 721 intervals (720 cap + 1) and the insufficient-candles warning is logged
    - `test_warm_up_warns_on_insufficient_candles` — verify warning logged when candle count < `strategy.warmup_candles` (covers both new listings and the 720-candle Kraken cap)
    - `test_warm_up_does_not_warn_when_sufficient_candles` — verify no warning when `len(candles) >= strategy.warmup_candles`
    - `test_warm_up_logs_completion_with_candle_count` — verify completion log includes the count of candles processed
    - `test_recover_state_restores_last_action` — verify `strategy.last_action` set from latest directional tick's signal (uses `get_latest_action_by_bot_id`)
    - `test_recover_state_skips_hold_ticks` — verify that if the most recent tick is HOLD but there's an earlier BUY tick, `last_action` is set to BUY (not HOLD)
    - `test_recover_state_first_run` — verify no error when no previous tick exists
    - `test_shutdown_marks_run_completed` — verify `bot_run_repo.complete()` called
    - `test_constructor_creates_and_persists_run` — verify `BotRun` created and added to repo
    - `test_execute_interval_dry_run_validates_without_placing` — verify `validate=True` passed to `AddOrderConnector.place()`, no `BotOrder` persisted, no `QueryOrdersConnector` calls, no tick persisted
    - `test_execute_interval_dry_run_logs_tick_without_persisting` — verify tick data (price, signal, balances) is logged but `bot_tick_repo.add()` is never called
    - `test_execute_interval_dry_run_skips_reconciliation` — verify `_reconcile_placed_orders` is a no-op in dry run mode (no PLACED orders exist to reconcile)

    *Regression tests — bugs fixed during review (don't specifically put these in their own test class or section):*
    - `test_execute_interval_tick_persistence_failure_logs_and_returns` — when `bot_tick_repo.add()` raises, error is logged and `execute_interval` returns without propagating; scheduler is not disrupted
    - `test_execute_interval_order_link_failure_logs_but_interval_completes` — when `bot_order_repo.update()` raises during `tick_id` linking, error is logged but the interval still completes (tick was already persisted; final log message fires)
    - `test_execute_interval_exception_after_order_persisted_tick_records_order_direction` — when an exception is raised after `placed_order` is set (e.g., `_fetch_balances` throws), the tick's `signal` is set to the order's actual direction (`BUY` or `SELL`), not `Signal.HOLD`; this ensures crash recovery via `recover_state` reads the correct `last_action`
    - `test_recover_state_reverses_signal_when_associated_order_failed` — when the order associated with the latest directional tick has `status=FAILED`, `last_action` is set to the *opposite* of the tick's signal (e.g., tick=SELL but order FAILED → `last_action=BUY`); guards against re-entering a position the bot never actually exited
    - `test_recover_state_uses_tick_signal_when_associated_order_filled` — when the associated order is FILLED, `last_action` is set to the tick's signal as normal (the position change is confirmed)
    - `test_recover_state_uses_tick_signal_when_no_order_for_tick` — when `get_by_tick_id` returns `None` (tick has no associated order, e.g., a HOLD tick or the order wasn't persisted), `last_action` is set to the tick's signal as normal
    - `test_execute_interval_bot_order_side_is_side_enum_not_signal_enum` — `BotOrder.side` is a `Side` instance, not a `Signal` instance; both are string enums with matching values so this only fails at the type level without an explicit test
    - `test_reconcile_exception_does_not_abort_interval` — if `_reconcile_placed_orders` raises, the exception is caught and logged, and `execute_interval` continues to fetch OHLC and produce a tick as normal; verifies the scheduler is never disrupted by a reconciliation outage
    - `test_execute_interval_failed_order_tick_has_hold_signal` — when `_confirm_order` returns a FAILED order, the persisted tick has `signal=Signal.HOLD` (not BUY/SELL); the order did not execute so the directional tick must not be recorded
    - `test_execute_interval_failed_order_tick_has_error_set` — when `_confirm_order` returns FAILED, `tick.error` is a non-None string describing the failure
    - `test_execute_interval_failed_order_still_linked_to_tick` — even when `_confirm_order` returns FAILED and signal becomes HOLD, the `placed_order` is still linked to the tick via `bot_order_repo.update(replace(placed_order, tick_id=tick.id))` — the order record exists and must point to its tick
    - `test_reconcile_does_not_roll_back_last_action_when_failed_order_side_differs` —edge case) if a FAILED order's side does not match the current `strategy.last_action`, `last_action` is left unchanged; prevents incorrectly flipping state when a stale previous-position order surfaces during reconciliation
    - `test_reconcile_per_order_exception_does_not_prevent_other_orders` — per-order try/except allows remaining orders in the batch to continue being reconciled even when one throws; verifies all N orders are attempted regardless of individual failures
    - `test_execute_interval_tick_has_timestamp_set` — `BotTick.timestamp` is set to a UTC datetime when the tick is persisted; regression guard against the required field being omitted from the `BotTick(...)` constructor call
    - All connectors and repositories are mocked (constructor is DI-based)

38. **Unit tests** for `AllInPositionSizer` at `tests/unit/trade_executor/test_position_sizer.py`.

39. **Integration test** at `tests/integration/test_trade_executor_integration.py`. Mock Kraken HTTP at the `requests.Session.request` level and mock Supabase repositories directly (not at the httpx transport layer — Supabase CRUD isn't the integration boundary being tested). Let `TradeExecutor` → exchange connectors → services → client stack all run. Verify end-to-end: OHLC fetch → strategy signal → order placement → query fill → tick persistence → order persistence.

40. **`QueryOrdersConnector` integration test** — mock only HTTP, let connector → service → client stack run with realistic Kraken response data.

41. **Register new pytest markers** in `pytest.ini`: `position_sizer`, `query_orders_service`, `query_orders_connector`, `trade_executor_integration`, `warmup_candles`.

42. **Add Makefile targets** to `Makefile`:
    - `test/trade_executor` — `pytest -m trade_executor`
    - `test/integration/trade_executor` — `pytest -m trade_executor_integration`

## Phase 9: Documentation + Housekeeping

43. **Update `docs/trade-executor.md`** with the new architecture: always-on process, BlockingScheduler + CronTrigger scheduling (with misfire protection), warm-up flow (using `Strategy.warmup_candles`), state recovery, order reconciliation loop, `PositionSizer` abstraction, `BotOrder` status lifecycle (PLACED → FILLED/FAILED with `filled_at`), DB-registered bots, `BotRun` lifecycle, graceful drain shutdown.

44. **Update `docs/cloud-architecture.md`** — replace Lambda/EventBridge with Fly.io always-on process. Update execution model, compute service, and deployment sections.

45. **Add architecture decisions** to `docs/architecture-decision-log.md`:
    - Chose Fly.io over Lambda (warm indicators, fewer API calls, simpler code)
    - Chose always-on + APScheduler over stateless invocations
    - Chose CronTrigger + jitter + 5s delay over IntervalTrigger
    - Chose BlockingScheduler over BackgroundScheduler
    - Chose `misfire_grace_time=0` and `max_instances=1` for trading safety
    - Chose DB-registered bot config over CLI args
    - Chose `QueryOrdersConnector` for accurate fill data over estimated values
    - Chose order reconciliation loop over single-attempt fill query
    - Chose to skip tick recording during warm-up
    - Chose `warmup_candles` as abstract Strategy property over hard-coded values
    - Chose `PositionSizer` abstraction over hardcoded all-in logic
    - Chose `BotOrder` status lifecycle (PLACED → FILLED) over atomic persist
    - Chose `filled_at` over `executed_at` — set on fill confirmation, not placement; added `placed_at` for crash-safe placement timestamps
    - Named `exchange_order_id` (not `txid`) in the domain layer — unambiguous against Kraken's trade IDs and ledger IDs visible in the Kraken web UI; `txid` is kept in the exchange connector layer where it matches Kraken's API terminology
    - Chose state recovery from latest *directional* tick (BUY/SELL only) over latest tick (which could be HOLD)
    - Chose to remove `IntervalContext` — private methods instead
    - Chose partial error ticks over sentinel values
    - Chose graceful drain shutdown over immediate shutdown
    - Chose dry run mode via Kraken's `validate=True` for zero-cost production verification

46. **Update `docs/exchange-connector/api-reference.md`** to document `QueryOrdersConnector` and `QueryOrderResult`.

---

## Verification

- `cd scalper && make test` — all existing tests pass
- `make test/trade_executor` — new executor tests pass
- `make test/exchange_connector` — new query order tests pass
- `make test/integration/trade_executor` — integration test passes
- `fly deploy --local-only` — Docker image builds successfully
- Manual dry run: `python -m scripts.register_bot --id test_bot_001 --pair BTCGBP --strategy-name PrecisionTrendStrategy --strategy-version v1.0.0 --interval 1 --parameters '{"short_ema": 43, ...}'` → verify bot appears in Supabase
- Manual dry run: `python -m scripts.start_scalping --bot-id test_bot_001 --dry-run` → verify state recovery logged, warm-up completes (using `strategy.warmup_candles` to determine history depth), no rows in `bot_ticks` or `bot_orders`, tick data and order validations visible in logs with `[DRY RUN]` prefix, scheduler fires at `:05` past each minute
- Manual live run: `python -m scripts.start_scalping --bot-id test_bot_001` → verify same as above but with real orders placed and persisted to `bot_orders`

---

## Operational Workflows

### Running locally via Docker

Build and run the container locally to verify the image before deploying, or to run a dry run against production Kraken/Supabase from your machine.

**Build the image:**
```sh
docker build -t crypto-scalper .
```

**Run with env file (recommended):** Your existing `.env` file contains all required credentials — pass it at runtime via `--env-file`. The `.dockerignore` excludes `.env` from the image; it is only injected at runtime.
```sh
docker run --env-file .env -e BOT_IDS=btc_1m_001 crypto-scalper
```

**Run dry run:**
```sh
docker run --env-file .env -e BOT_IDS=btc_1m_001 -e DRY_RUN=true crypto-scalper
```

`BOT_IDS` is not in `.env` (it's a Fly.io env var, not a secret), so pass it separately with `-e`. All other vars (`KRAKEN_TRADING_API_KEY`, `KRAKEN_TRADING_API_SECRET`, `SUPABASE_URL`, `SUPABASE_KEY`) come from `.env`.

### Deploying code updates

`fly deploy` is the only deployment command. The full lifecycle:

1. `fly deploy` builds and pushes the new Docker image
2. Fly.io sends `SIGTERM` to the running container
3. Signal handler calls `executor.request_shutdown()` on each executor — sets `_shutting_down = True`; any in-flight `execute_interval()` completes (including order placement and fill query), but the next scheduled interval returns immediately
4. `scheduler.shutdown(wait=True)` blocks until running jobs finish
5. `executor.shutdown()` marks each `BotRun` as completed via `bot_run_repo.complete()`
6. Process exits, old container is removed
7. New container starts with the updated image
8. `entrypoint.sh` parses `BOT_IDS` env var and launches `start_scalping.py`
9. For each bot: `_recover_state()` restores `strategy.last_action` from the latest directional (BUY/SELL) tick
10. For each bot: `warm_up()` fetches OHLC history and replays through the strategy to rebuild indicator state
11. Scheduler starts — bots resume trading on the next wall-clock-aligned interval

**Safety guarantees:** No order placement is interrupted mid-flight (graceful drain). At most 1 interval is missed during the container swap (~30s). State is fully recovered from Supabase — no in-memory state is lost. `BotRun` records cleanly delineate pre- and post-deploy activity.

### Adding a new bot

1. Register the bot in Supabase: `python -m scripts.register_bot --id eth_5m_v2 --pair XETHZGBP --strategy-name PrecisionTrendStrategy --strategy-version v1.0.0 --interval 5 --parameters '{"short_ema": 43, ...}'`
2. Update the `BOT_IDS` env var on Fly.io: `fly secrets set BOT_IDS=btc_1m_001,eth_5m_v2`
3. Deploy: `fly deploy`

The new bot starts with `_recover_state()` finding no previous ticks (first run), warms up from OHLC history, and begins trading. Existing bots recover their state from their latest ticks and resume normally. No code changes needed — bot config lives entirely in the database.

### Removing a bot

1. Update `BOT_IDS` to exclude the bot: `fly secrets set BOT_IDS=btc_1m_001`
2. Deploy: `fly deploy`

The removed bot's `BotRun` from the previous deployment was already marked complete during graceful shutdown. Its historical data (`bot_ticks`, `bot_orders`, `bot_runs`) remains in Supabase for analysis. The `Bot` record can optionally be left in the `bots` table (inert — only bots in `BOT_IDS` are started).

### Updating bot parameters

Bot parameters (strategy windows, thresholds) are read from Supabase at startup. To update:

1. Update the `Bot` record in Supabase (directly or via a future `update_bot.py` script)
2. Deploy: `fly deploy` (or restart: `fly apps restart crypto-scalper`)

The bot picks up the new parameters on restart, warms up with the updated strategy config, and resumes. **Note:** changing parameters mid-run without restart has no effect — parameters are read once during `TradeExecutor` construction.

### Crash recovery

Fly.io auto-restarts the container on crash (typically <30s). The recovery sequence:

1. New container starts → `entrypoint.sh` → `start_scalping.py`
2. `_recover_state()` queries `bot_tick_repo.get_latest_action_by_bot_id()` — restores `strategy.last_action` from the most recent directional (BUY/SELL) tick's signal, preventing position-unaware double buys
3. `warm_up()` replays OHLC history through the strategy to rebuild indicator state (one API call, milliseconds of computation)
4. `_reconcile_placed_orders()` runs at the start of the first `execute_interval()` — any orders placed before the crash that were left in PLACED status are checked against Kraken and resolved (FILLED or FAILED)
5. Scheduler resumes normal operation

**Worst case:** 1 missed interval. The crashed `BotRun` remains with `completed_at IS NULL` — detectable for monitoring/alerting.

### Monitoring bot health

Query `bot_ticks` timestamps to verify bots are active:

```sql
SELECT bot_id, MAX(timestamp) AS last_tick
FROM bot_ticks
GROUP BY bot_id;
```

A gap exceeding the bot's interval + grace period indicates a problem. Persistent gaps during OHLC failures are expected and acceptable — they surface in the logs via `fly logs`.

Unfinished runs indicate crashes:

```sql
SELECT id, bot_id, started_at
FROM bot_runs
WHERE completed_at IS NULL;
```

---

## Decisions

- **Fly.io over Lambda:** Warm indicators stay in memory, halves Kraken API calls, simpler deployment and code. ~$2/month vs free but operationally complex. After warm-up, seed value carries ~5% weight in the EMA — most consequential at crossover boundaries where scalping decisions flip. Always-on eliminates this by maintaining continuous indicator state after a one-time warm-up.
- **Fly.io over VPS:** Container abstraction (`fly deploy`) is simpler than managing OS, systemd, SSH, and monitoring on a VPS, for comparable cost ($2-3/month vs $4-6/month).
- **APScheduler with CronTrigger and BlockingScheduler:** Battle-tested scheduling library. `BlockingScheduler` is the correct choice for a single-purpose script — it blocks the main thread after `start()` and integrates cleanly with signal handlers via `shutdown(wait=True)`. `CronTrigger` provides wall-clock alignment (fires at `:00`, `:05`, etc.), unlike `IntervalTrigger` which fires relative to start time. 5-second offset handles Kraken data propagation delay. Jitter (3s) prevents simultaneous API calls from multiple bots.
- **Misfire protection (`misfire_grace_time=0`, `max_instances=1`):** If `execute_interval()` for one bot runs long (Kraken slow, network issues), the next scheduled execution is skipped rather than queued. `max_instances=1` ensures only one instance runs per bot at a time. Critical for trading safety — prevents stacking intervals that could cause double-orders or stale data.
- **IntervalContext removed:** Too thin to justify as a class — just two wrapper methods over connectors. Transformation logic (extracting latest closed candle, balance key lookup, string→Decimal conversion) lives in private `TradeExecutor` methods (`_fetch_ohlc()`, `_fetch_balances()`). Less indirection, one fewer class.
- **PositionSizer abstraction:** Injectable component with `AllInPositionSizer` default (buy → `balances.balance_quote`, sell → `balances.balance_base`). Enables future strategies (grid trading, DCA, partial fills) without modifying `TradeExecutor`. Interface: `calculate_volume(signal, balances: PairBalances) -> Decimal`. `PairBalances` is a frozen dataclass (fields: `symbol_base: str`, `symbol_quote: str`, `balance_base: Decimal`, `balance_quote: Decimal`) defined in `trade_executor/position_sizer.py`. It merges the symbol lookup from `get_kraken_pair_symbols()` with the actual balance amounts — `_fetch_balances()` constructs one per interval and `pair_symbols` never needs to travel beyond the executor. Consistent with project frozen dataclass conventions; field names align with the `balance_base`/`balance_quote` convention used in `BotTick` and avoid ambiguity between symbol strings and balance amounts.
- **BotOrder status lifecycle (PLACED → FILLED) with `placed_at` and `filled_at`:** After `AddOrderConnector.place()` succeeds, extract `exchange_order_id = order_result.txid[0]` (Kraken returns a list; simple market orders always produce a single-element list). Immediately persist a partial `BotOrder` with `exchange_order_id`, status=PLACED, `placed_at=datetime.now(utc)`, fill fields nullable, `filled_at=None`. Then retry QueryOrders up to 3 times (1s apart) checking for Kraken's `status='closed'`. On fill confirmation: update with price/volume/fee, `filled_at=datetime.now(utc)`, status=FILLED via `dataclasses.replace()` (frozen dataclass). If still `open` after 3 attempts: leave as PLACED — will be reconciled at the start of the next interval. If `cancelled`: mark FAILED. `placed_at` records submission time directly on the order (independent of tick persistence — if the process crashes between order placement and tick persist, placement time is still recorded). `filled_at` records when fill confirmation arrived from QueryOrders.
- **Per-interval order reconciliation:** Every `execute_interval` starts by querying for outstanding PLACED orders and checking their status via QueryOrders. All outstanding `exchange_order_id` values are collected and sent in a single `QueryOrdersConnector.fetch(exchange_order_ids)` call — Kraken's endpoint accepts multiple order IDs in one request, so N PLACED orders cost one API call, not N. This handles market orders that take slightly longer than expected and naturally supports future limit orders (which may take minutes/hours to fill or be cancelled). No order stays in PLACED limbo indefinitely.
- **State recovery from latest directional tick:** On startup (before warm-up), query `bot_tick_repo.get_latest_action_by_bot_id()` which filters for `signal IN ('buy', 'sell')`. `strategy.last_action` is only ever `BUY` or `SELL` (never `HOLD`) — it tracks the last directional action for consecutive-signal suppression. Recovering from a HOLD tick would corrupt this: e.g., bot buys → holds for 20 intervals → crash → recovery sets `last_action=HOLD` → next BUY signal passes suppression → double buy. The filtered query ensures `last_action` is always restored to a valid directional state.
- **Warm-up via `Strategy.warmup_candles` property:** Each strategy declares its own warm-up requirement as an abstract property computed from its configured indicator windows (e.g., PrecisionTrendStrategy: `3 × max(window sizes)`, SmaStrategy: `long_window + 1`). The 3× multiplier is the standard EMA convergence heuristic — after 3× the window length, the seed value carries ~5% weight in the EMA. Changing indicator windows in `strategy_configs.py` automatically adjusts the warm-up requirement — no strategy code changes needed. `TradeExecutor.warm_up()` calls `_fetch_ohlc_history()` to get the full candle batch, then feeds each candle through `strategy.generate_signal()` sequentially.
- **Partial error ticks:** If OHLC fetch fails → log error, skip tick (can't construct BotTick without non-nullable price/balance fields). If strategy or order placement fails → persist tick with `error` field set (price data is available). Clean data in `bot_ticks` — every row has real values.
- **Graceful drain shutdown:** On `SIGTERM`/`SIGINT`, call `executor.request_shutdown()` on each executor — this sets the internal `_shutting_down` flag (checked at start of `execute_interval()`, prevents new intervals from doing work) without exposing the private attribute to external mutation. Then call `scheduler.shutdown(wait=True)` which blocks until any currently-running jobs finish. Then call `executor.shutdown()` on each executor to mark runs complete. Prevents interrupted order placements during `fly deploy`. No additional reconciliation is needed in `shutdown()`: the preceding `scheduler.shutdown(wait=True)` already ensures the running interval completes — including its own `_reconcile_placed_orders()` call and the post-order QueryOrders retry loop. Any order still `PLACED` after that belongs to the next run to resolve, via the same `get_placed_by_bot_id()` query used for crash recovery.
- **`exchange_order_id` in domain layer, `txid` in exchange connector layer:** Kraken uses `txid` to mean the order ID — distinct from the trade IDs and ledger IDs also visible in the Kraken web UI. In the exchange connector layer (`QueryOrderResult.txid`, `AddOrderResult.txid`, `QueryOrdersService`), `txid` is kept as-is — it matches the Kraken API and that layer is intentionally Kraken-specific. In the domain layer (`BotOrder`, `bot_orders` table), the field is named `exchange_order_id` — self-documenting without requiring Kraken API knowledge, unambiguous when reading the schema alongside trade IDs and ledger IDs. The mapping `exchange_order_id = order_result.txid[0]` happens in `TradeExecutor` at the connector→domain boundary.
- **`QueryOrdersConnector` for fill data:** `BotOrder` requires `price`, `volume`, `fee` as `Decimal` — estimated values would compromise the data integrity the schema is designed for.
- **Skip ticks during warm-up:** Warm-up signals are mathematically incomplete (EMA hasn't converged). Recording them would pollute the decision log with unreliable data.
- **Warm-up validation — warn and continue:** If Kraken returns fewer candles than `strategy.warmup_candles`, log a warning but start anyway. Refusing to start would prevent new trading pairs from ever running.
- **Kraken 720-candle hard limit:** Kraken's OHLC endpoint returns at most 720 of the most recent candles. Older data cannot be retrieved regardless of `since` — pagination is not possible. `_fetch_ohlc_history()` requests `min(warmup_candles, 720)` candles. If `warmup_candles > 720`, the warm-up is partial and the existing warning covers it. `PrecisionTrendStrategy`'s maximum warm-up is 237 candles (well within the limit). `SmaStrategy` with Optuna-optimised `long_window > 719` would be affected, but that scenario is deferred — solving it requires a different data source (e.g., warm-up from stored local trades). Not a blocker for current live strategies.
- **Per-bot `BotRun` lifecycle:** Run is created when executor starts, marked complete on graceful shutdown. Unfinished runs (crash) are detectable by `completed_at IS NULL`.
- **Single process over per-bot containers (for now):** 2-5 bots have negligible memory footprint in one process. Evolves naturally to Fly.io Machines API if scaling to 10+ bots, with no changes to `TradeExecutor` itself.
- **Post-suppression signal in BotTick:** Store the final signal the bot acted on (after consecutive-signal suppression), not the raw strategy output.
- **One bot per currency pair (for now):** `AllInPositionSizer` assumes exclusive access to the pair's balances (buy → full quote balance, sell → full base balance). Running multiple bots on the same or overlapping currency pairs (e.g., BTCGBP and BTCUSD sharing BTC base) would cause them to compete for balances. A future `BalanceAwarePositionSizer` could partition balances across bots, but for now the constraint is one bot per currency pair.
- **`strategy_version` is metadata only:** `Bot.strategy_version` is stored in Supabase for auditing and debugging (e.g., "which version of PrecisionTrendStrategy was this bot running?"). It is *not* used by `create_strategy()` or the executor at runtime.
- **Health monitoring via bot_ticks:** Query `MAX(timestamp)` from `bot_ticks` grouped by `bot_id` to check bot health. No schema changes needed. Gaps in ticks during OHLC failures are acceptable — if OHLC is failing repeatedly, that's worth knowing about.
- **Text logging for now:** Use existing `LOG_FORMAT` from utils. Logs go to stderr via `logging.basicConfig()`, which Fly.io captures and exposes via `fly logs` — adequate for monitoring during initial deployment. Switch to JSON structured logging when a log aggregation sink (Datadog, Loki) is added — one-line change in the entry-point formatter.
- **Entrypoint script for multi-bot Docker:** `entrypoint.sh` parses comma-separated `BOT_IDS` env var into `--bot-id` flags, with validation that `BOT_IDS` is set and non-empty. Cleaner than embedding CLI flag format in env vars.
- **`auto_stop_machines = false` in `fly.toml`:** Explicitly prevents Fly.io from stopping the machine when it detects no inbound HTTP traffic. Critical for an always-on trading bot that only makes outbound API calls.
- **Post-trade balance recording:** For BUY/SELL intervals, balances are fetched *after* the order flow so `BotTick` records reflect the bot's actual position after acting on its signal. For HOLD intervals, balances are fetched directly (no order flow).
- **Dry run mode via Kraken's `validate=True`:** `AddOrderConnector.place()` already accepts a `validate` parameter — Kraken validates the order (pair, volume, balance) without executing it, returning an `AddOrderResult` with `txid=None` and the order description. In dry run mode: orders are validated but not placed, no `BotOrder` is persisted (no `exchange_order_id` to track), `QueryOrdersConnector` is not called, and **no ticks are persisted** — all tick data is logged instead. This prevents dry run data from polluting `bot_ticks` and, critically, from corrupting `_recover_state()` when switching to live: if the last dry run tick recorded signal=BUY, the live bot would think it already holds a position it never bought, skipping its first real entry. Logs include a `[DRY RUN]` prefix on all output lines. This enables verifying the full OHLC → signal → order-validation loop in production before risking real money. Zero additional API cost — Kraken's validate endpoint is free. Activated via `--dry-run` CLI flag or `DRY_RUN=true` env var in Docker.
- **Current executor requires full rewrite regardless of platform:** The existing `TradeExecutor` calls `generate_signal(price)` with a `float`, but `Strategy.generate_signal()` expects a `pd.Series` with `open`, `high`, `low`, `close` keys. No persistence, no warm-up, no DI. Both stateless and always-on approaches require the same rewrite scope — platform choice doesn't affect implementation effort.

### Future extension points

The following capabilities are **not in scope** for this plan but are **not blocked** by the architecture:

- **Stop-losses / take-profits:** Would require a position monitor component that runs between intervals (not just interval-based decisions). The `BotOrder` model and `QueryOrdersConnector` provide the foundation for tracking open positions.
- **Multi-timeframe strategies:** Would require signal aggregation across multiple `TradeExecutor` instances (e.g., 1m and 15m charts for the same pair). The single-bot `execute_interval` model would need a coordinator layer.
- **Risk-aware position sizing:** `PositionSizer.calculate_volume()` currently receives a `PairBalances` instance (amounts + symbol names). A future `RiskAwarePositionSizer` (e.g., Kelly criterion, volatility-scaled sizing) would need additional context such as open orders, position history, or unrealised P&L. The interface can be extended without modifying `TradeExecutor`.

---

## Architecture Rationale

### Why always-on over stateless

The core argument is **signal accuracy at crossover boundaries**. EMA indicators are infinite impulse response (IIR) filters — their "true" value depends on *all* historical data, not just the last N candles. A stateless approach that cold-starts from ~240 candles of OHLC history means the seed value still carries ~$e^{-3} \approx 5\%$ weight in the EMA output. The actual prediction error depends on how far the seed is from the true EMA — for a well-chosen seed the error is smaller, but at crossover boundaries where EMAs are close together, even small biases can flip the signal. Fetching 720 candles (Kraken's max per call) reduces seed weight to ~$e^{-9} \approx 0.01\%$ but still isn't zero.

These errors are smallest in absolute terms but **most consequential at EMA crossover boundaries** — precisely where scalping signals flip between BUY and HOLD. The entire purpose of Optuna parameter optimisation is to find precise EMA windows and thresholds; running those optimised parameters against cold-start EMAs undermines that precision.

An always-on process warms up once on startup, then maintains continuous indicator state in memory. Every subsequent signal is mathematically identical to running the strategy against complete historical data. This is the gold standard.

### API call efficiency

Stateless: each interval requires fetching ~240 OHLC candles to replay through the strategy, plus balance + maybe trade = heavier API load per interval.

Always-on: each interval fetches 1 OHLC candle + balance + maybe trade. Warm-up replay happens once on startup (single API call — Kraken returns up to 720 candles, sufficient for all current live strategies). Halves the per-interval Kraken API footprint.

### Alternatives evaluated

- **Stateless Lambda + EventBridge** — ❌ Rejected
  EMA convergence error on every invocation; 5-6 AWS services (Lambda, ECR, EventBridge, IAM,
  CloudWatch, Terraform) adds operational complexity that far exceeds the ~$2/month saving; some
  free tier services expire after 12 months; adding a bot requires Terraform changes, not a DB
  insert.

- **Stateless with persisted indicator state** — ❌ Rejected
  Serialising EMA/RSI/ADX internal state to Supabase adds a round-trip read on every invocation,
  serialisation complexity per indicator, and a state schema maintenance burden whenever an
  indicator changes. Trades simplicity for a ~$2/month saving — not worthwhile.

- **Always-on VPS (DigitalOcean/Hetzner)** — ❌ Rejected
  ~$4-6/month with the added burden of managing OS updates, SSH access, systemd, and monitoring.
  More operational overhead than Fly.io's container abstraction for marginal benefit.

- **Per-bot Fly.io Machines** — ⏳ Deferred
  Good future path for 10+ bots (complete isolation, independent scaling), but overkill for 2-5
  bots at ~$2-3/month per machine. The single-process APScheduler design evolves to this without
  changes to `TradeExecutor` — only the entry-point script changes.

- **Always-on Fly.io** — ✅ Chosen
  Perfect signal accuracy after warm-up, ~$2/month total, simplest deployment (`fly deploy`),
  DB-registered bots mean adding a bot is a DB insert not an infra change, auto-restart on crash.

### Scalability path

Current target: 2-5 bots in a single process (negligible memory per bot — indicators use bounded `deque`s).

Future: if scaling beyond ~10 bots, migrate to Fly.io Machines API — one container per bot. The `TradeExecutor` class is identical; only the entry-point script changes from "N bots in one process" to "1 bot per container".

### Fault tolerance

Process crash → Fly.io auto-restart (typically <30s) → state recovery from latest directional tick → warm-up replay (~milliseconds of computation, single OHLC API call) → scheduler resumes. At most 1 interval is missed on crash. Unfinished `BotRun` records (where `completed_at IS NULL`) are detectable for monitoring/alerting.