---
name: add-kraken-endpoint
description: Add a new Kraken API endpoint to scalper/exchange_connector/ following the Client/Service/Connector layered pattern. Use when the user wants to expose a new Kraken endpoint (public or private), wrap an unsupported Kraken call, or asks to "add a connector", "add a Kraken endpoint", or scaffold something like "AddOrder", "Ticker", "OHLC", "WithdrawStatus" etc. Walks the standard workflow - service → connector → domain model (if needed) → exports → tests → markers.
---

# Add Kraken Endpoint

Add a new Kraken API endpoint to `scalper/exchange_connector/` using the project's three-layer
Client / Service / Connector pattern (see `.claude/rules/architecture.md`).

The shared `KrakenApiClient` already handles HTTP, signing, and error parsing — almost every new
endpoint only needs a service, a connector, and (usually) a domain model.

---

## What this skill produces

```
scalper/exchange_connector/
├── services/
│   ├── {name}_service.py            # new
│   └── __init__.py                  # add export
├── connectors/
│   ├── {name}_connector.py          # new
│   └── __init__.py                  # add export
├── models/
│   ├── {name}_result.py             # only if a domain object is warranted
│   └── __init__.py                  # add export (if model added)
└── __init__.py                      # re-export connector + model

scalper/tests/unit/exchange_connector/
├── connectors/test_connectors.py    # append a Test{Name}Connector class
└── services/test_services.py        # append a Test{Name}Service class
```

Plus updates to `pytest.ini` (two new class-level markers) and optionally a small CLI under
`scalper/scripts/`.

---

## How to use this skill

1. **Clarify requirements first.** Confirm:
   - Endpoint name and HTTP method (GET / POST).
   - Path on Kraken (e.g. `/0/public/Ticker`, `/0/private/AddOrder`) and HTTP method. Private
     endpoints are always POST; `KrakenApiClient` signs every POST automatically (public GETs
     are unsigned).
   - Inputs the caller passes and what shape the raw Kraken response has.
   - Whether the response deserves a domain model (frozen dataclass) or can stay as a `dict`
     pass-through (see "Domain model — when to add one" below).
2. **Check existing exemplars.** Pick the closest match and copy its shape:

   ```bash
   ls scalper/exchange_connector/connectors
   ls scalper/exchange_connector/services
   ```

   - Read-only public data → look at `ticker_connector.py` (no domain model) or
     `ohlc_connector.py` (with `OhlcCandle` model).
   - Paginated / multi-call fetch → `trades_service.py`.
   - Authenticated action → `add_order_connector.py` + `add_order_service.py`.
3. **Walk `checklist.md`** in order. It is the source of truth for the workflow, file paths, and
   acceptance criteria. Tick each box as you go — don't skip ahead.
4. **Use `templates.md` as scaffolding.** It contains four labelled blocks (service, connector,
   optional domain model, tests). Copy the relevant block, then replace every `{{placeholder}}`.
   The templates encode the layer-responsibility split (validation in service, transformation in
   connector) so you don't have to reconstruct it from prose.
5. **Stop and ask** before:
   - Modifying `KrakenApiClient` or `kraken_service.py` (shared infrastructure — affects every
     endpoint).
   - Adding a new dependency (`uv add ...`).
   - Doing anything in `trade_executor/` or `scripts/start_scalping.py` (live trading paths).

---

## Domain model — when to add one

Add a frozen dataclass under `models/` when **any** of these are true:

- The raw response shape is awkward (nested dicts, positional arrays, cryptic keys).
- Callers across the project will read the same fields.
- The endpoint will likely be reused for backtesting, persistence, or UI.

Skip the model and return the raw `dict` (or `dict[str, Any]`) when:

- It's a one-off ad-hoc query (e.g. `Ticker` for a CLI).
- The response is already a flat, well-named dict.

`AddOrderResult`, `OhlcCandle`, and `QueryOrderResult` are good model exemplars; `TickerConnector`
shows the dict pass-through.

---

## Files in this skill

- `SKILL.md` — this file (overview + how to use).
- `checklist.md` — the workflow, file paths, and acceptance criteria.
- `templates.md` — copy-paste scaffolds for service, connector, model, and tests.

For style/architecture rules (layered architecture, dependency injection, validate-at-boundaries,
frozen dataclasses, type hints, British English, test marker hierarchy), see `CLAUDE.md`,
`.claude/rules/architecture.md`, `.claude/rules/testing.md`, and `.claude/rules/docstrings.md`.
