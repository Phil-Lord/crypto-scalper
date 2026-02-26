# Plan: Trade Executor + Live Trading on Fly.io

**TL;DR:** Rewrite the trade executor module as an always-on process that loads bot config from Supabase, recovers state from the latest persisted tick, warms up strategy indicators from OHLC history, runs a CronTrigger scheduler per bot interval (with jitter and fixed delay), and persists every tick and order to Supabase. Build a `QueryOrderConnector` in the exchange connector to fetch fill details from Kraken after order placement. Extend `BotOrder` with `status`/`txid` fields for order safety — persist immediately after placement, update on fill. Add an injectable `PositionSizer` abstraction for volume calculation. Deploy as a Docker container on Fly.io with `fly deploy`. The core executor is platform-agnostic — Fly.io specifics are confined to the Dockerfile, `fly.toml`, `entrypoint.sh`, and the entry-point script.

**Key decisions reflected:**
- Platform: Fly.io (~$2/month), CronTrigger + jitter + 5s delay
- Bot config: DB-registered (looked up from Supabase `bots` table by `bot_id`)
- Warm-up: Skip recording ticks until indicators are ready; warn if insufficient candles
- Order fills: Build `QueryOrderConnector` to retrieve actual execution details
- Order safety: Extend `BotOrder` with `status`/`txid`; persist immediately after placement
- State recovery: Query latest tick on startup to restore `strategy.last_action`
- Volume: Injectable `PositionSizer` with `AllInPositionSizer` default
- No `IntervalContext`: Transformation logic lives in private `TradeExecutor` methods
- Error ticks: Skip on OHLC failure; persist with error field when price data available
- Graceful shutdown: Flag blocks new intervals; wait for in-progress interval to finish
- Health monitoring: Use `bot_ticks` timestamps — no schema changes needed
- Logging: Text format for now; switch to JSON when a log sink is added

---

**Steps**

## Phase 1: Exchange Connector — QueryOrder Support

1. **Add `QueryOrderService`** at `exchange_connector/services/query_order_service.py`. Inherits `KrakenService`. Calls Kraken's `POST /0/private/QueryOrders` endpoint with `txid` param. Returns raw dict of order details keyed by txid. Kraken response includes `price` (average executed price), `vol_exec` (volume executed), and `fee`.

2. **Add `OrderFill` domain model** at `exchange_connector/models/order_fill.py`. Frozen dataclass with fields: `txid: str`, `price: Decimal`, `volume: Decimal`, `fee: Decimal`, `status: str`. This is the typed representation of a filled order's execution details.

3. **Add `QueryOrderConnector`** at `exchange_connector/connectors/query_order_connector.py`. Inherits `FetchConnector`. Method: `fetch(txids: list[str]) -> list[OrderFill]`. Delegates to `QueryOrderService`, transforms raw response into `OrderFill` domain objects by extracting `price`, `vol_exec`, and `fee` from each order entry.

4. **Export new symbols** from `exchange_connector/__init__.py` — add `QueryOrderConnector` and `OrderFill`. Also export from `exchange_connector/models/__init__.py` and `exchange_connector/connectors/__init__.py`.

5. **Unit tests** for `QueryOrderService` and `QueryOrderConnector` in `tests/unit/exchange_connector/`. Follow existing patterns (e.g., `TestAddOrderConnector`). Test happy path, error parsing, multi-txid response, and `_to_domain` conversion. Register markers `query_order_service` and `query_order_connector` in `pytest.ini`.

## Phase 2: Data System — Model + Repository Extensions

6. **Extend `BotOrder` model** at `data_system/models/bot_order_model.py`:
    - Add `OrderStatus(str, Enum)`: `PLACED = 'placed'`, `FILLED = 'filled'`, `FAILED = 'failed'`
    - Add `txid: str` field
    - Add `status: OrderStatus` field (default `PLACED`)
    - Make `price`, `volume`, `fee` optional: `Decimal | None = None`
    - Make `tick_id` optional: `int | None = None` (may not have tick ID at placement time)

7. **Update `bot_orders` schema** in `data_system/schema.sql`:
    - Add `txid TEXT NOT NULL`
    - Add `status TEXT NOT NULL DEFAULT 'placed'` with `CHECK (status IN ('placed', 'filled', 'failed'))`
    - Make `price`, `volume`, `fee` nullable: `DECIMAL(32, 12)` (remove NOT NULL)
    - Make `tick_id` nullable (already is — `REFERENCES` without NOT NULL)

8. **Add `update()` method to `BotOrderRepository`** at `data_system/repositories/bot_order/bot_order_repository.py`. Signature: `update(self, bot_order: BotOrder) -> BotOrder`. Updates an existing order record (used to fill in price/volume/fee after QueryOrders succeeds).

9. **Implement `update()` in `SupabaseBotOrderRepository`** at `data_system/repositories/bot_order/supabase_bot_order_repository.py`.

10. **Add `complete()` method to `BotRunRepository`** at `data_system/repositories/bot_run/bot_run_repository.py`. Signature: `complete(self, id: UUID, completed_at: datetime) -> BotRun`. Abstract method to mark a run as finished by setting `completed_at`.

11. **Implement `complete()` in `SupabaseBotRunRepository`** at `data_system/repositories/bot_run/supabase_bot_run_repository.py`. Uses `client.table('bot_runs').update({'completed_at': completed_at.isoformat()}).eq('id', str(id)).execute()`, then returns the deserialised `BotRun`.

12. **Add `get_latest_by_bot_id()` to `BotTickRepository`** at `data_system/repositories/bot_tick/bot_tick_repository.py`. Signature: `get_latest_by_bot_id(self, bot_id: str) -> BotTick | None`. Returns the most recent tick for a bot (needed to determine last known state on restart).

13. **Implement `get_latest_by_bot_id()` in `SupabaseBotTickRepository`** at `data_system/repositories/bot_tick/supabase_bot_tick_repository.py`. Query with `.eq('bot_id', bot_id).order('timestamp', desc=True).limit(1)`.

14. **Unit tests** for all new/modified repository methods and the updated `BotOrder` model. Follow existing patterns in `tests/unit/data_system/`.

15. **Update `data_system` exports** — export `OrderStatus` from `data_system/models/__init__.py` and `data_system/__init__.py`.

## Phase 3: Position Sizing

16. **Add `PositionSizer` abstract base class** at `trade_executor/position_sizer.py`. Interface: `calculate_volume(self, signal: Signal, balances: tuple[Decimal, Decimal], pair_symbols: dict) -> Decimal`. ABC with a single abstract method.

17. **Add `AllInPositionSizer`** in the same file. Implements `calculate_volume()`: buy → full quote balance, sell → full base balance. This replicates current behaviour.

18. **Unit tests** for `AllInPositionSizer` at `tests/unit/trade_executor/test_position_sizer.py`.

## Phase 4: Trade Executor — Core Rewrite

19. **Delete** the current `trade_executor/config.py` and `trade_executor/handler.py`. These are Lambda artefacts being replaced.

20. **Delete `IntervalContext`** at `trade_executor/interval_context.py`. Transformation logic moves to private `TradeExecutor` methods (`_fetch_ohlc()`, `_fetch_balances()`).

21. **Rewrite `TradeExecutor`** at `trade_executor/trade_executor.py`. Complete redesign:

    - **Constructor** takes dependency-injected components:
      - `bot: Bot` — configuration from Supabase
      - `strategy: Strategy` — created from `bot.strategy_name` + `bot.parameters` via `create_strategy()`
      - `position_sizer: PositionSizer` — injectable, default `AllInPositionSizer`
      - `bot_run_repo: BotRunRepository`
      - `bot_tick_repo: BotTickRepository`
      - `bot_order_repo: BotOrderRepository`
      - Connectors: `OhlcConnector`, `BalanceConnector`, `AddOrderConnector`, `QueryOrderConnector`
    - Stores `pair_symbols` from `get_kraken_pair_symbols(bot.pair)`
    - Creates `run: BotRun` on construction and persists it via `bot_run_repo.add()`
    - Has `self._shutting_down: bool = False` flag for graceful drain
    - **`_recover_state(self) -> None`**: Queries latest tick via `bot_tick_repo.get_latest_by_bot_id(bot.id)`. If found, sets `strategy.last_action` from tick's signal. Logs recovery details or 'first run' if no tick exists.
    - **`_fetch_ohlc(self) -> pd.Series`**: Private method. Fetches latest OHLC via `OhlcConnector`, extracts the latest closed candle from the raw array, returns as `pd.Series` with keys `price`, `open`, `high`, `low`, `close` matching what `Strategy.generate_signal()` expects.
    - **`_fetch_balances(self) -> tuple[Decimal, Decimal]`**: Private method. Fetches balances via `BalanceConnector`, looks up symbols using `pair_symbols`, converts string values to `Decimal`, handles missing keys (zero balance). Returns `(balance_base, balance_quote)`.
    - **`warm_up(self) -> None`**: Fetches historical OHLC candles via `OhlcConnector`, feeds them sequentially through `strategy.generate_signal()` to warm up indicators. Calculates appropriate `since` timestamp from `bot.interval` and the strategy's warm-up requirement (derive from indicator windows). Logs progress but does **not** persist ticks during warm-up.
        - **Warm-up validation**: After fetching, check that candle count meets the strategy's minimum warm-up requirement. If insufficient (e.g., new trading pair), log a warning that signals may be unreliable for the first N intervals. Concrete requirements: PrecisionTrendStrategy needs ~240 candles (3× longest EMA window of 79), SmaStrategy needs ~201 candles (long_window + 1 for crossover detection). Bot starts anyway (warn and continue).
    - **`execute_interval(self) -> None`**: One decision cycle:
      1. Check `self._shutting_down` — if True, return immediately (graceful drain)
      2. Fetch latest closed OHLC candle via `self._fetch_ohlc()`. If this fails, log error and return (no tick persisted — required fields are non-nullable)
      3. Call `strategy.generate_signal(ohlc)` → extract post-suppression `Signal` from result dict
      4. Fetch balances via `self._fetch_balances()`
      5. If signal is `BUY` or `SELL`:
          - Calculate volume via `position_sizer.calculate_volume(signal, balances, pair_symbols)`
          - Place order via `AddOrderConnector.place()` → get `OrderResult` with txid
          - **Immediately persist** partial `BotOrder` with txid, status=`PLACED`, fill fields=`None`
          - Query fill via `QueryOrderConnector.fetch(txid)` with short delay (~1s)
          - On fill success: update `BotOrder` with price/volume/fee, status=`FILLED` via `bot_order_repo.update()`
          - On fill failure: log critical warning with txid for manual reconciliation, update status=`FAILED`
      6. Construct `BotTick` with `bot_id`, `run_id`, `timestamp`, `price` (from OHLC), `signal` (post-suppression), `balance_base`, `balance_quote`
      7. Persist tick via `bot_tick_repo.add()` → get back tick with DB-generated `id`
      8. If order was placed: update `BotOrder` with `tick_id` from persisted tick via `bot_order_repo.update()`
      9. Log results
    - **Error handling**: If OHLC fetch fails → log error, return (no tick — can't construct BotTick without price). If strategy or order placement fails → persist tick with `error` field set, log error, continue. On fatal errors (Supabase unreachable): log and let the process crash (Fly.io auto-restarts).
    - **`shutdown(self) -> None`**: Marks the run as completed via `bot_run_repo.complete(self.run.id, datetime.now(timezone.utc))`.
    - **No `load_env()`** or `logging.basicConfig()` — these stay in the entry-point script only.
    - **No internal connector instantiation** — all injected via constructor.

22. **Update `trade_executor/__init__.py`**. Export `TradeExecutor`, `PositionSizer`, `AllInPositionSizer`.

## Phase 5: Scheduler + Entry Point

23. **Add `apscheduler` and `supabase` to `requirements.txt`**. (`supabase` is currently missing despite being imported by Supabase repositories.)

24. **Rewrite `start_scalping.py`** at `scripts/start_scalping.py`. New flow:
    - `load_env()` + `logging.basicConfig()` (entry-point responsibilities)
    - Click CLI: `--bot-id` (required, `multiple=True`). Example: `--bot-id btc_1m_001 --bot-id eth_5m_v2`
    - For each `bot_id`:
      1. Look up `Bot` from Supabase via `SupabaseBotRepository.get(bot_id)` — fail if not found
      2. Create strategy via `create_strategy(bot.strategy_name, bot.parameters)`
      3. Create `AllInPositionSizer()` (or future: select sizer from config)
      4. Instantiate `TradeExecutor` with all dependencies (repositories, connectors, strategy, position sizer, bot)
      5. Call `executor._recover_state()` — restore `last_action` from latest persisted tick
      6. Call `executor.warm_up()` — blocks until indicators are ready
      7. Schedule `executor.execute_interval` with APScheduler using **`CronTrigger`** aligned to wall-clock + **5-second offset** + **`jitter=3`** (e.g., `CronTrigger(minute='*', second=5)` for 1-min interval, `CronTrigger(minute='*/5', second=5)` for 5-min). The 5-second offset handles Kraken data propagation delay. Jitter prevents simultaneous API calls from multiple bots.
    - Register signal handlers for `SIGTERM`/`SIGINT`:
      1. Set `_shutting_down = True` on each executor (prevents new intervals from starting)
      2. Wait for any in-progress interval to complete
      3. Call `executor.shutdown()` on each executor
      4. Stop APScheduler and exit
    - Start the APScheduler and block

25. **Add `register_bot.py`** at `scripts/register_bot.py`. Click CLI to insert a `Bot` record into Supabase. Options: `--id`, `--pair`, `--strategy-name`, `--strategy-version`, `--interval`, `--parameters` (JSON string). This is a helper for initial bot setup — run once per bot before starting the executor.

## Phase 6: Deployment — Fly.io

26. **Create `Dockerfile`** at project root. Multi-stage build:
    - Base: `python:3.12-slim`
    - Install dependencies from `requirements.txt`
    - Copy `scalper/` source
    - Copy `entrypoint.sh`
    - `ENTRYPOINT ["./entrypoint.sh"]`

27. **Create `entrypoint.sh`** at project root. Parses comma-separated `BOT_IDS` env var into `--bot-id` flags. Example: `BOT_IDS=btc_1m_001,eth_5m_v2` → `python -m scripts.start_scalping --bot-id btc_1m_001 --bot-id eth_5m_v2`. Adding a bot requires updating the `BOT_IDS` env var and running `fly deploy` (restart is safe — warm-up replays history, `_recover_state()` restores position).

28. **Create `fly.toml`** at project root. Configuration:
    - `app = 'crypto-scalper'`
    - Region: `lhr` (London — closest to Kraken EU)
    - Machine: `shared-cpu-1x`, 256MB RAM
    - No HTTP service (internal process, no ports exposed)
    - Auto-restart: `restart` policy on failure

29. **Create `.dockerignore`** — exclude `legacy/`, `docs/`, `site/`, `.git/`, `__pycache__/`, `*.pyc`, `local_storage/`, `logs/`, `.env`

30. **Secrets management**: Kraken API keys and Supabase credentials stored as Fly.io secrets (`fly secrets set KRAKEN_API_KEY=... KRAKEN_API_SECRET=... SUPABASE_URL=... SUPABASE_KEY=...`). These become environment variables in the container — the existing `SupabaseConfig` metaclass and `os.getenv` patterns already handle this.

## Phase 7: Tests

31. **Rewrite unit tests** for `TradeExecutor` at `tests/unit/trade_executor/test_trade_executor.py`. New tests covering:
    - `test_execute_interval_buy_persists_tick_and_order` — verify tick repo receives `BotTick` with correct fields, order repo receives `BotOrder` with txid and status=PLACED, then updated to FILLED with fill details from `QueryOrderConnector`
    - `test_execute_interval_hold_persists_tick_only` — no order placed, tick still recorded
    - `test_execute_interval_sell_persists_tick_and_order` — sell path
    - `test_execute_interval_ohlc_failure_skips_tick` — when OHLC fetch throws, no tick persisted, error logged
    - `test_execute_interval_strategy_error_persists_tick_with_error` — when strategy throws, tick is saved with `error` field
    - `test_execute_interval_query_fill_failure_logs_critical` — order placed (PLACED persisted) but fill query fails; verify critical log with txid
    - `test_execute_interval_skipped_when_shutting_down` — verify early return when `_shutting_down` is True
    - `test_warm_up_feeds_candles_sequentially` — verify OHLC fetched and each candle fed through `generate_signal()`, no ticks persisted
    - `test_warm_up_calculates_correct_since_timestamp` — verify the `since` param to `OhlcConnector.fetch()` covers enough history
    - `test_warm_up_warns_on_insufficient_candles` — verify warning logged when candle count < requirement
    - `test_recover_state_restores_last_action` — verify `strategy.last_action` set from latest tick's signal
    - `test_recover_state_first_run` — verify no error when no previous tick exists
    - `test_shutdown_marks_run_completed` — verify `bot_run_repo.complete()` called
    - `test_constructor_creates_and_persists_run` — verify `BotRun` created and added to repo
    - All connectors and repositories are mocked (constructor is DI-based)

32. **Unit tests** for `AllInPositionSizer` at `tests/unit/trade_executor/test_position_sizer.py`.

33. **Integration test** at `tests/integration/test_trade_executor_integration.py`. Mock only Kraken HTTP and Supabase client. Let `TradeExecutor` → connectors → services all run. Verify end-to-end: OHLC fetch → strategy signal → order placement → query fill → tick persistence → order persistence.

34. **`QueryOrderConnector` integration test** — mock only HTTP, let connector → service → client stack run with realistic Kraken response data.

35. **Register new pytest markers** in `pytest.ini`: `position_sizer`, `query_order_service`, `query_order_connector`, `trade_executor_integration`.

36. **Add Makefile targets** to `Makefile`:
    - `test/trade_executor` — `pytest -m trade_executor`
    - `test/integration/trade_executor` — `pytest -m trade_executor_integration`

## Phase 8: Documentation + Housekeeping

37. **Update `docs/trade-executor.md`** with the new architecture: always-on process, CronTrigger scheduling, warm-up flow, state recovery, `PositionSizer` abstraction, `BotOrder` status lifecycle, DB-registered bots, `BotRun` lifecycle, graceful drain shutdown.

38. **Update `docs/cloud-architecture.md`** — replace Lambda/EventBridge with Fly.io always-on process. Update execution model, compute service, and deployment sections.

39. **Add architecture decisions** to `docs/architecture-decision-log.md`:
    - Chose Fly.io over Lambda (warm indicators, fewer API calls, simpler code)
    - Chose always-on + APScheduler over stateless invocations
    - Chose CronTrigger + jitter + 5s delay over IntervalTrigger
    - Chose DB-registered bot config over CLI args
    - Chose `QueryOrderConnector` for accurate fill data over estimated values
    - Chose to skip tick recording during warm-up
    - Chose `PositionSizer` abstraction over hardcoded all-in logic
    - Chose `BotOrder` status lifecycle (PLACED → FILLED) over atomic persist
    - Chose state recovery from latest tick over cold-start defaults
    - Chose to remove `IntervalContext` — private methods instead
    - Chose partial error ticks over sentinel values
    - Chose graceful drain shutdown over immediate shutdown

40. **Update `docs/exchange-connector/api-reference.md`** to document `QueryOrderConnector` and `OrderFill`.

---

## Verification

- `cd scalper && make test` — all existing tests pass
- `make test/trade_executor` — new executor tests pass
- `make test/exchange_connector` — new query order tests pass
- `make test/integration/trade_executor` — integration test passes
- `fly deploy --local-only` — Docker image builds successfully
- Manual dry run: `python -m scripts.register_bot --id test_bot_001 --pair BTCGBP --strategy-name PrecisionTrendStrategy --strategy-version v1.0.0 --interval 1 --parameters '{"short_ema": 43, ...}'` → verify bot appears in Supabase
- Manual test: `python -m scripts.start_scalping --bot-id test_bot_001` → verify state recovery logged, warm-up completes, first tick appears in `bot_ticks` table, scheduler fires at `:05` past each minute

---

## Decisions

- **Fly.io over Lambda:** Warm indicators stay in memory, halves Kraken API calls, simpler deployment and code. ~$2/month vs free but operationally complex. EMA convergence error from cold-start replay (~5% at 240 candles) is most consequential at crossover boundaries where scalping decisions flip. Always-on eliminates this by maintaining continuous indicator state after a one-time warm-up.
- **Fly.io over VPS:** Container abstraction (`fly deploy`) is simpler than managing OS, systemd, SSH, and monitoring on a VPS, for comparable cost ($2-3/month vs $4-6/month).
- **APScheduler with CronTrigger:** Battle-tested scheduling library. `CronTrigger` provides wall-clock alignment (fires at `:00`, `:05`, etc.), unlike `IntervalTrigger` which fires relative to start time. 5-second offset handles Kraken data propagation delay. Jitter (3s) prevents simultaneous API calls from multiple bots.
- **IntervalContext removed:** Too thin to justify as a class — just two wrapper methods over connectors. Transformation logic (extracting latest closed candle, balance key lookup, string→Decimal conversion) lives in private `TradeExecutor` methods (`_fetch_ohlc()`, `_fetch_balances()`). Less indirection, one fewer class.
- **PositionSizer abstraction:** Injectable component with `AllInPositionSizer` default (buy → full quote balance, sell → full base balance). Enables future strategies (grid trading, DCA, partial fills) without modifying `TradeExecutor`. Interface: `calculate_volume(signal, balances, pair_symbols) -> Decimal`.
- **BotOrder status lifecycle (PLACED → FILLED):** After `AddOrderConnector.place()` succeeds, immediately persist a partial `BotOrder` with txid and status=PLACED (fill fields nullable). Then query fill details and update to FILLED. If QueryOrders fails, the txid is preserved for manual reconciliation. Protects against lost fill data.
- **State recovery from latest tick:** On startup (before warm-up), query `bot_tick_repo.get_latest_by_bot_id()`. If a previous tick exists, set `strategy.last_action` from its signal. Prevents position-unaware double buys after crash-restart.
- **Partial error ticks:** If OHLC fetch fails → log error, skip tick (can't construct BotTick without non-nullable price/balance fields). If strategy or order placement fails → persist tick with `error` field set (price data is available). Clean data in `bot_ticks` — every row has real values.
- **Graceful drain shutdown:** On `SIGTERM`/`SIGINT`, set `_shutting_down` flag on each executor (checked at start of `execute_interval()`). Wait for any in-progress interval to complete, then call `shutdown()`. Prevents interrupted order placements during `fly deploy`.
- **`QueryOrderConnector` for fill data:** `BotOrder` requires `price`, `volume`, `fee` as `Decimal` — estimated values would compromise the data integrity the schema is designed for.
- **Skip ticks during warm-up:** Warm-up signals are mathematically incomplete (EMA hasn't converged). Recording them would pollute the decision log with unreliable data.
- **Warm-up validation — warn and continue:** If Kraken returns fewer candles than the strategy's warm-up requirement, log a warning but start anyway. Refusing to start would prevent new trading pairs from ever running.
- **Per-bot `BotRun` lifecycle:** Run is created when executor starts, marked complete on graceful shutdown. Unfinished runs (crash) are detectable by `completed_at IS NULL`.
- **Single process over per-bot containers (for now):** 2-5 bots have negligible memory footprint in one process. Evolves naturally to Fly.io Machines API if scaling to 10+ bots, with no changes to `TradeExecutor` itself.
- **Post-suppression signal in BotTick:** Store the final signal the bot acted on (after consecutive-signal suppression), not the raw strategy output.
- **Health monitoring via bot_ticks:** Query `MAX(timestamp)` from `bot_ticks` grouped by `bot_id` to check bot health. No schema changes needed. Gaps in ticks during OHLC failures are acceptable — if OHLC is failing repeatedly, that's worth knowing about.
- **Text logging for now:** Use existing `LOG_FORMAT` from utils. Switch to JSON structured logging when a log aggregation sink (Datadog, Loki) is added — one-line change in the entry-point formatter.
- **Entrypoint script for multi-bot Docker:** `entrypoint.sh` parses comma-separated `BOT_IDS` env var into `--bot-id` flags. Cleaner than embedding CLI flag format in env vars.
- **Current executor requires full rewrite regardless of platform:** The existing `TradeExecutor` calls `generate_signal(price)` with a `float`, but `Strategy.generate_signal()` expects a `pd.Series` with `price`, `high`, `low` keys. No persistence, no warm-up, no DI. Both stateless and always-on approaches require the same rewrite scope — platform choice doesn't affect implementation effort.

---

## Architecture Rationale

### Why always-on over stateless

The core argument is **signal accuracy at crossover boundaries**. EMA indicators are infinite impulse response (IIR) filters — their "true" value depends on *all* historical data, not just the last N candles. A stateless approach that cold-starts from ~240 candles of OHLC history carries a convergence error of ~$e^{-3} \approx 5\%$ in the EMA values. Even fetching 720 candles (Kraken's max per call) only reduces this to ~$e^{-9} \approx 0.01\%$.

These errors are smallest in absolute terms but **most consequential at EMA crossover boundaries** — precisely where scalping signals flip between BUY and HOLD. The entire purpose of Optuna parameter optimisation is to find precise EMA windows and thresholds; running those optimised parameters against cold-start EMAs undermines that precision.

An always-on process warms up once on startup, then maintains continuous indicator state in memory. Every subsequent signal is mathematically identical to running the strategy against complete historical data. This is the gold standard.

### API call efficiency

Stateless: each interval requires fetching ~240 OHLC candles to replay through the strategy, plus balance + maybe trade = heavier API load per interval.

Always-on: each interval fetches 1 OHLC candle + balance + maybe trade. Warm-up replay happens once on startup (single API call, Kraken returns up to 720 candles). Halves the per-interval Kraken API footprint.

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

Process crash → Fly.io auto-restart (typically <30s) → state recovery from latest tick → warm-up replay (~milliseconds of computation, one OHLC API call) → scheduler resumes. At most 1 interval is missed on crash. Unfinished `BotRun` records (where `completed_at IS NULL`) are detectable for monitoring/alerting.