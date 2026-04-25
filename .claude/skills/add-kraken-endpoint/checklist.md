# Add-Kraken-Endpoint Checklist

Work through this top to bottom. Each step has its own acceptance criteria — don't tick a step
until those criteria are met.

`{{name}}` here is the snake_case endpoint name (e.g. `withdraw_status`); `{{Name}}` is the
PascalCase form (`WithdrawStatus`).

---

## 1. Scaffold the service

- [ ] File at `scalper/exchange_connector/services/{{name}}_service.py`
- [ ] Subclasses `KrakenService` (do **not** subclass `object` — you'd lose retry + auth)
- [ ] Calls `self.validate_pair(pair)` if the endpoint takes a trading pair
- [ ] Returns `self.make_request(method, endpoint, params)` (or its result keyed by pair) — the
      base class already strips the outer `result` envelope and applies retry/back-off
- [ ] Endpoint path uses the Kraken convention: `/0/public/...` or `/0/private/...` (the latter
      auto-signs via `KrakenApiClient`)
- [ ] No retry decorator added here — `KrakenService.make_request` already retries on
      `KrakenTooManyRequestsError`
- [ ] Pagination, if needed, lives in this layer (see `trades_service.py` for the pattern: loop
      with a moving cursor, terminate on a sentinel, use `tqdm` for progress)

Template: see "Service" in `templates.md`.

## 2. Add the domain model (only if warranted)

See "Domain model — when to add one" in `SKILL.md`. Skip this step for raw-dict endpoints.

- [ ] File at `scalper/exchange_connector/models/{{name}}_result.py`
- [ ] `@dataclass(frozen=True)` with required fields first, defaulted last
- [ ] Every attribute documented in the class docstring (see `.claude/rules/docstrings.md`)
- [ ] Uses `Decimal` for any monetary value used by live trading; `float` is fine for stats and
      Unix timestamps
- [ ] Exported from `scalper/exchange_connector/models/__init__.py`

Template: see "Domain model" in `templates.md`.

## 3. Scaffold the connector

- [ ] File at `scalper/exchange_connector/connectors/{{name}}_connector.py`
- [ ] Subclasses `FetchConnector` (read-only) or `PlaceConnector` (mutating action)
- [ ] `__init__(self, client: KrakenApiClient | None = None)` — defaulted client so scripts can
      construct it bare, but injectable for tests
- [ ] Instantiates the service in `__init__` (e.g. `self.service = {{Name}}Service(self.client)`)
- [ ] Public method (`fetch` or `place`) has full type hints, single-quoted reST docstring with
      `:param:` and `:return:` lines, and uses an enum in the type hint where a fixed value set
      exists (e.g. order side)
- [ ] Domain transformation lives in `_to_domain` (or returns the raw dict if no model). Wrap
      parsing in `try/except (ValueError, TypeError, KeyError, IndexError, AttributeError)` and
      re-raise as `ValueError` with context — validate-at-boundaries (see
      `.claude/rules/architecture.md`)

Template: see "Connector" in `templates.md`.

## 4. Update exports

- [ ] Add to `scalper/exchange_connector/connectors/__init__.py`
- [ ] Add to `scalper/exchange_connector/services/__init__.py`
- [ ] If a model was added: add to `scalper/exchange_connector/models/__init__.py`
- [ ] Add the connector (and any model) to `scalper/exchange_connector/__init__.py` so callers
      can `from exchange_connector import {{Name}}Connector`

## 5. Write tests

The exchange-connector unit tests are organised as **two big files** holding one class per
endpoint, not one file per endpoint. Append your class — don't create a new file.

- [ ] `Test{{Name}}Connector` class appended to
      `scalper/tests/unit/exchange_connector/connectors/test_connectors.py`
- [ ] `Test{{Name}}Service` class appended to
      `scalper/tests/unit/exchange_connector/services/test_services.py`
- [ ] Cover for the connector: client injection, default-client construction, happy path
      (`service` mocked), `_to_domain` happy path, `_to_domain` raises `ValueError` on each
      malformed-response shape you can think of (missing fields, wrong types, empty payload)
- [ ] Cover for the service: pair validation rejects bad input (if applicable), `make_request`
      called with the correct method/endpoint/params, response unwrapping
- [ ] If pagination: assert termination on the sentinel and that `time.sleep` is patched so the
      test runs fast (see `.claude/rules/testing.md`)

Template: see "Connector tests" and "Service tests" in `templates.md`.

## 6. Register pytest markers

- [ ] Add the two new class-level markers to `pytest.ini`:

      ```
      {{name}}_connector: Tests for the {{Name}}Connector class.
      {{name}}_service: Tests for the {{Name}}Service class.
      ```

- [ ] Module/category markers (`exchange_connector`, `connectors`, `services`) are reused — do
      **not** redefine them

## 7. Optional CLI

- [ ] If the user wants ad-hoc access, add a script under `scalper/scripts/` mirroring an
      existing example (loads env, configures logging, exposes a `click` command). Naming
      convention is loose — existing scripts use `get_{{name}}.py` for read-only fetches
      (`get_ticker.py`, `get_balances.py`), `fetch_{{name}}.py` for paginated fetches
      (`fetch_trades.py`), and bare `{{name}}.py` for actions (`add_order.py`,
      `query_orders.py`)
- [ ] Scripts call `load_env()` **before** importing modules that read env at import time
- [ ] Scripts are not importable production code — keep business logic in the connector

---

## Final acceptance

- [ ] `pytest -m {{name}}_connector and pytest -m {{name}}_service` both pass
- [ ] `pytest -m exchange_connector` still passes (no regression)
- [ ] No `Optional`, `Union`, `List`, `Dict` from `typing` introduced
- [ ] Single quotes throughout, British English in identifiers and prose
- [ ] Public method on the connector takes domain types in / returns domain types out (or raw
      `dict` consistently) — no leaking of Kraken's positional-array response shape past the
      connector boundary
- [ ] Retry, signing, and HTTP error handling are all delegated to the existing layers — your
      new code does not re-implement any of them
