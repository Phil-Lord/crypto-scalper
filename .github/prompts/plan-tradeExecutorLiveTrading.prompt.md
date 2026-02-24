# Plan: Trade Executor + Live Trading on Fly.io

**TL;DR:** Rewrite the trade executor module as an always-on process that loads bot config from Supabase, warms up strategy indicators from OHLC history on startup, runs an internal scheduler per bot interval, and persists every tick and order to Supabase. Build a new `QueryOrderConnector` in the exchange connector to fetch fill details (price, volume, fee) from Kraken after order placement. Deploy as a Docker container on Fly.io with `fly deploy`. The core executor is platform-agnostic — Fly.io specifics are confined to the Dockerfile, `fly.toml`, and the entry-point script.

**Key decisions reflected:**
- Platform: Fly.io (~$2/month)
- Bot config: DB-registered (looked up from Supabase `bots` table by `bot_id`)
- Warm-up: Skip recording ticks until indicators are ready
- Order fills: Build `QueryOrderConnector` to retrieve actual execution details

---

**Steps**

## Phase 1: Exchange Connector — QueryOrder Support

1. **Add `QueryOrderService`** at `exchange_connector/services/query_order_service.py`. Inherits `KrakenService`. Calls Kraken's `POST /0/private/QueryOrders` endpoint with `txid` param. Returns raw dict of order details keyed by txid. Kraken response includes `price` (average executed price), `vol_exec` (volume executed), and `fee`.

2. **Add `OrderFill` domain model** at `exchange_connector/models/order_fill.py`. Frozen dataclass with fields: `txid: str`, `price: Decimal`, `volume: Decimal`, `fee: Decimal`, `status: str`. This is the typed representation of a filled order's execution details.

3. **Add `QueryOrderConnector`** at `exchange_connector/connectors/query_order_connector.py`. Inherits `FetchConnector`. Method: `fetch(txids: list[str]) -> list[OrderFill]`. Delegates to `QueryOrderService`, transforms raw response into `OrderFill` domain objects by extracting `price`, `vol_exec`, and `fee` from each order entry.

4. **Export new symbols** from `exchange_connector/__init__.py` — add `QueryOrderConnector` and `OrderFill`. Also export from `exchange_connector/models/__init__.py`.

5. **Unit tests** for `QueryOrderService` and `QueryOrderConnector` in `tests/unit/exchange_connector/`. Follow existing patterns (e.g., `TestAddOrderConnector`). Test happy path, error parsing, multi-txid response, and `_to_domain` conversion. Register markers `query_order_service` and `query_order_connector` in `pytest.ini`.

## Phase 2: Data System — Repository Extensions

6. **Add `complete()` method to `BotRunRepository`** at `data_system/repositories/bot_run/bot_run_repository.py`. Signature: `complete(self, id: UUID, completed_at: datetime) -> BotRun`. Abstract method to mark a run as finished by setting `completed_at`.

7. **Implement `complete()` in `SupabaseBotRunRepository`** at `data_system/repositories/bot_run/supabase_bot_run_repository.py`. Uses `client.table('bot_runs').update({'completed_at': completed_at.isoformat()}).eq('id', str(id)).execute()`, then returns the deserialised `BotRun`.

8. **Add `get_latest_by_bot_id()` to `BotTickRepository`** at `data_system/repositories/bot_tick/bot_tick_repository.py`. Signature: `get_latest_by_bot_id(self, bot_id: str) -> BotTick | None`. Returns the most recent tick for a bot (needed to determine last known state on restart).

9. **Implement `get_latest_by_bot_id()` in `SupabaseBotTickRepository`** at `data_system/repositories/bot_tick/supabase_bot_tick_repository.py`. Query with `.order('timestamp', desc=True).limit(1)`.

10. **Unit tests** for the new repository methods. Follow existing patterns in `tests/unit/data_system/repositories/`.

11. **Update `data_system` exports** if any new symbols need exporting (the new methods are on existing classes, so no new exports needed — but verify).

## Phase 3: Trade Executor — Core Rewrite

12. **Delete** the current `trade_executor/config.py` and `trade_executor/handler.py`. These are Lambda artefacts being replaced.

13. **Rewrite `IntervalContext`** at `trade_executor/interval_context.py`. This is the state handler for each interval. It encapsulates:
    - **Input state:** Current balances (from `BalanceConnector.fetch()`), latest OHLC candle (from `OhlcConnector.fetch()`), current tick timestamp
    - **Output state:** The recorded `BotTick` (with its DB-generated `id`), the `OrderFill` if a trade was placed
    - Constructor takes `pair: str`, `interval: int`, and the connector instances. Provides methods:
      - `fetch_ohlc(self, pair: str, interval: int) -> pd.Series` — fetches latest closed candle from Kraken OHLC, returns as a `pd.Series` with keys `price`, `open`, `high`, `low`, `close` matching what `Strategy.generate_signal()` expects
      - `fetch_balances(self, base_symbol: str, quote_symbol: str) -> tuple[Decimal, Decimal]` — fetches balances, returns `(balance_base, balance_quote)` as `Decimal`
    - This is a lightweight data-fetching layer, not a persistence layer. Persistence is handled by the executor directly via repositories.

14. **Rewrite `TradeExecutor`** at `trade_executor/trade_executor.py`. Complete redesign:

    - **Constructor** takes dependency-injected components:
      - `bot: Bot` — configuration from Supabase
      - `strategy: Strategy` — created from `bot.strategy_name` + `bot.parameters` via `create_strategy()`
      - `bot_run_repo: BotRunRepository`
      - `bot_tick_repo: BotTickRepository`
      - `bot_order_repo: BotOrderRepository`
      - Connectors: `OhlcConnector`, `TickerConnector`, `BalanceConnector`, `AddOrderConnector`, `QueryOrderConnector`
    - Stores `pair_symbols` from `get_kraken_pair_symbols(bot.pair)`
    - Creates `run: BotRun` on construction and persists it via `bot_run_repo.add()`
    - **`warm_up(self) -> None`**: Fetches historical OHLC candles via `OhlcConnector`, feeds them sequentially through `strategy.generate_signal()` to warm up indicators. Calculates appropriate `since` timestamp from `bot.interval` and the strategy's warm-up requirement (derive from indicator windows). Logs progress but does **not** persist ticks during warm-up.
        - **Warm-up validation**: After fetching historical OHLC candles, check that the number of candles returned meets the strategy's minimum warm-up requirement. If Kraken returns fewer candles than needed (e.g., new trading pair with limited history), log a warning that signals may be unreliable for the first N intervals after the gap. Concrete warm-up requirements: PrecisionTrendStrategy needs ~240 candles (3× longest EMA window of 79), SmaStrategy needs ~201 candles (long_window + 1 for crossover detection).
    - **`execute_interval(self) -> None`**: One decision cycle:
      1. Fetch latest closed OHLC candle via `IntervalContext.fetch_ohlc()`
      2. Call `strategy.generate_signal(ohlc)` → extract `Signal` from result dict
      3. Fetch balances via `IntervalContext.fetch_balances()`
      4. If signal is `BUY` or `SELL`: place order via `AddOrderConnector.place()`, then fetch fill details via `QueryOrderConnector.fetch(txid)`, construct `BotOrder` with actual `price`, `volume`, `fee`
      5. Construct `BotTick` with `bot_id`, `run_id`, `timestamp`, `price` (from OHLC), `signal`, `balance_base`, `balance_quote`
      6. Persist tick via `bot_tick_repo.add()` → get back tick with DB-generated `id`
      7. If order was placed: set `tick_id` on `BotOrder` from the persisted tick's `id`, persist via `bot_order_repo.add()`
      8. Log results
    - **`shutdown(self) -> None`**: Marks the run as completed via `bot_run_repo.complete(self.run.id, datetime.now(timezone.utc))`
    - **Error handling**: Wrap `execute_interval()` in try/except. On error: still persist a `BotTick` with the `error` field set, log the error, continue (don't crash the process). On fatal errors (Supabase unreachable): log and let the process crash (Fly.io will auto-restart).
    - **No `load_env()`** or `logging.basicConfig()` — these stay in the entry-point script only
    - **No internal connector instantiation** — all injected via constructor

15. **Update `trade_executor/__init__.py`**. Export `TradeExecutor` and `IntervalContext`.

## Phase 4: Scheduler + Entry Point

16. **Add `apscheduler` to `requirements.txt`**. Also add `supabase` (currently missing from requirements despite being imported by the Supabase repositories).

17. **Rewrite `start_scalping.py`** at `scripts/start_scalping.py`. New flow:
    - `load_env()` + `logging.basicConfig()` (entry-point responsibilities)
    - Click CLI: `--bot-id` (required, one or more). Example: `--bot-id btc_1m_001 --bot-id eth_5m_v2`
    - For each `bot_id`:
      1. Look up `Bot` from Supabase via `SupabaseBotRepository.get(bot_id)` — fail if not found
      2. Create strategy via `create_strategy(bot.strategy_name, bot.parameters)`
      3. Instantiate `TradeExecutor` with all dependencies (repositories, connectors, strategy, bot)
      4. Call `executor.warm_up()` — blocks until indicators are ready
      5. Schedule `executor.execute_interval` with APScheduler at `IntervalTrigger(minutes=bot.interval)`, aligned to wall-clock intervals (e.g., 1-min interval fires at :00, :01, :02...)
    - Register signal handlers for `SIGTERM`/`SIGINT` to call `executor.shutdown()` on each executor before exit (graceful shutdown on `fly deploy` or process stop)
    - Start the APScheduler and block

18. **Add a `register_bot.py` script** at `scripts/register_bot.py`. Click CLI to insert a `Bot` record into Supabase. Options: `--id`, `--pair`, `--strategy-name`, `--strategy-version`, `--interval`, `--parameters` (JSON string). This is a helper for initial bot setup — run once per bot before starting the executor.

## Phase 5: Deployment — Fly.io

19. **Create `Dockerfile`** at project root. Multi-stage build:
    - Base: `python:3.12-slim`
    - Install dependencies from `requirements.txt`
    - Copy `scalper/` source
    - `CMD`: `python -m scripts.start_scalping --bot-id $BOT_ID`
    - `BOT_ID` comes from Fly.io environment variable (set via `fly secrets`)

20. **Create `fly.toml`** at project root. Configuration:
    - `app = 'crypto-scalper'`
    - Region: `lhr` (London — closest to Kraken EU)
    - Machine: `shared-cpu-1x`, 256MB RAM
    - No HTTP service (internal process, no ports exposed)
    - Auto-restart: `restart` policy on failure
    - `BOT_ID` env var set per deployment

21. **Create `.dockerignore`** — exclude `legacy/`, `docs/`, `site/`, `.git/`, `__pycache__/`, `*.pyc`, `local_storage/`, `logs/`, `.env`

22. **Secrets management**: Kraken API keys and Supabase credentials stored as Fly.io secrets (`fly secrets set KRAKEN_API_KEY=... KRAKEN_API_SECRET=... SUPABASE_URL=... SUPABASE_KEY=...`). These become environment variables in the container — the existing `SupabaseConfig` metaclass and `os.getenv` patterns already handle this.

## Phase 6: Tests

23. **Rewrite unit tests** for `TradeExecutor` at `tests/unit/trade_executor/test_trade_executor.py`. New tests covering:
    - `test_execute_interval_buy_persists_tick_and_order` — verify tick repo receives `BotTick` with correct fields, order repo receives `BotOrder` with fill details from `QueryOrderConnector`
    - `test_execute_interval_hold_persists_tick_only` — no order placed, tick still recorded
    - `test_execute_interval_sell_persists_tick_and_order` — sell path
    - `test_execute_interval_error_persists_tick_with_error` — when strategy throws, tick is saved with `error` field
    - `test_warm_up_feeds_candles_sequentially` — verify OHLC fetched and each candle fed through `generate_signal()`, no ticks persisted
    - `test_warm_up_calculates_correct_since_timestamp` — verify the `since` param to `OhlcConnector.fetch()` covers enough history
    - `test_shutdown_marks_run_completed` — verify `bot_run_repo.complete()` called
    - `test_constructor_creates_and_persists_run` — verify `BotRun` created and added to repo
    - All connectors and repositories are mocked (constructor is DI-based)

24. **Add `IntervalContext` unit tests** at `tests/unit/trade_executor/test_interval_context.py`. Test `fetch_ohlc()` returns correct `pd.Series` format, `fetch_balances()` returns `Decimal` tuple.

25. **Add integration test** at `tests/integration/test_trade_executor_integration.py`. Mock only Kraken HTTP and Supabase client. Let `TradeExecutor` → `IntervalContext` → connectors → services all run. Verify end-to-end: OHLC fetch → strategy signal → order placement → query fill → tick persistence → order persistence.

26. **Add `QueryOrderConnector` integration test** — mock only HTTP, let connector → service → client stack run with realistic Kraken response data.

27. **Register new pytest markers** in `pytest.ini`: `interval_context`, `query_order_service`, `query_order_connector`, `trade_executor_integration`.

28. **Add Makefile targets** to `Makefile`:
    - `test/trade_executor` — `pytest -m trade_executor`
    - `test/trade_executor/interval_context` — `pytest -m "trade_executor and interval_context"`
    - `test/integration/trade_executor` — `pytest -m trade_executor_integration`

## Phase 7: Documentation + Housekeeping

29. **Update `docs/trade-executor.md`** with the new architecture: always-on process, APScheduler, `IntervalContext` as data-fetching layer, warm-up flow, DB-registered bots, `BotRun` lifecycle.

30. **Update `docs/cloud-architecture.md`** — replace Lambda/EventBridge with Fly.io always-on process. Update execution model, compute service, and deployment sections.

31. **Add architecture decisions** to `docs/architecture-decision-log.md`:
    - Chose Fly.io over Lambda (warm indicators, fewer API calls, simpler code)
    - Chose always-on + APScheduler over stateless invocations
    - Chose DB-registered bot config over CLI args
    - Chose `QueryOrderConnector` for accurate fill data over estimated values
    - Chose to skip tick recording during warm-up

32. **Update `docs/exchange-connector/api-reference.md`** to document `QueryOrderConnector` and `OrderFill`.

33. **Add `supabase` to `requirements.txt`** if not already present (it's imported but not listed).

---

## Verification

- `cd scalper && make test` — all existing tests pass
- `make test/trade_executor` — new executor tests pass
- `make test/exchange_connector` — new query order tests pass
- `make test/integration/trade_executor` — integration test passes
- `fly deploy --local-only` — Docker image builds successfully
- Manual dry run: `python -m scripts.register_bot --id test_bot_001 --pair BTCGBP --strategy-name PrecisionTrendStrategy --strategy-version v1.0.0 --interval 1 --parameters '{"short_ema": 43, ...}'` → verify bot appears in Supabase
- Manual test: `python -m scripts.start_scalping --bot-id test_bot_001` → verify warm-up completes, first tick appears in `bot_ticks` table, scheduler fires at the expected interval

---

## Decisions

- **Fly.io over Lambda:** Warm indicators stay in memory, halves Kraken API calls, simpler deployment and code. ~$2/month vs free but operationally complex. EMA convergence error from cold-start replay (~5% at 240 candles) is most consequential at crossover boundaries where scalping decisions flip. Always-on eliminates this by maintaining continuous indicator state after a one-time warm-up.
- **Fly.io over VPS:** Container abstraction (`fly deploy`) is simpler than managing OS, systemd, SSH, and monitoring on a VPS, for comparable cost ($2-3/month vs $4-6/month).
- **APScheduler over `asyncio`/`time.sleep` loop:** Battle-tested scheduling library with wall-clock alignment, missed-job handling, and clean shutdown. Avoids reimplementing cron logic.
- **`IntervalContext` as data-fetching layer, not persistence layer:** Keeps `TradeExecutor` as the single owner of persistence logic. `IntervalContext` only transforms connector outputs into the format `TradeExecutor` needs.
- **`QueryOrderConnector` for fill data:** `BotOrder` requires `price`, `volume`, `fee` as `Decimal` — estimated values would compromise the data integrity the schema is designed for.
- **Skip ticks during warm-up:** Warm-up signals are mathematically incomplete (EMA hasn't converged). Recording them would pollute the decision log with unreliable data.
- **Per-bot `BotRun` lifecycle:** Run is created when executor starts, marked complete on graceful shutdown. Unfinished runs (crash) are detectable by `completed_at IS NULL`.
- **Single process over per-bot containers (for now):** 2-5 bots have negligible memory footprint in one process. Evolves naturally to Fly.io Machines API if scaling to 10+ bots, with no changes to `TradeExecutor` itself.
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

Process crash → Fly.io auto-restart (typically <30s) → warm-up replay (~milliseconds of computation, one OHLC API call) → scheduler resumes. At most 1 interval is missed on crash. Unfinished `BotRun` records (where `completed_at IS NULL`) are detectable for monitoring/alerting.
