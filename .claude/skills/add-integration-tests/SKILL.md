---
name: add-integration-tests
description: Add or update integration tests in scalper/tests/integration/ that exercise multiple layers together with only system boundaries mocked. Use when the user asks to "add integration tests", "add an integration test for X", "cover the connector → service → client flow", or after a change that genuinely spans layers (new connector, new repository hitting a new client path, cross-module data flow). Push back if the request is really a unit-test job. For unit tests, this is the wrong skill.
---

# Add Integration Tests

Add or update integration tests in `scalper/tests/integration/` that exercise multiple layers
of the system together — connector → service → client, repository → client → DB session,
strategy + indicator + rule pipelines — with mocks **only** at system boundaries (HTTP, the
database session, file I/O, `time.sleep`).

> Scope: **integration tests only.** If the change is contained to a single class or function,
> it's a unit-test job — flag that, point the user at the `add-unit-tests` skill, and stop.
> Don't pad the integration suite with tests that belong in `tests/unit/`.

---

## Tests are a spec, not a snapshot

The job is to test what the stack is **supposed** to do, then check it does that. Not to test
what it **currently** does and call it covered.

The failure mode to avoid: wire up the layers, run the flow, observe the output, paste it
into an `assert`. That builds a regression net for whatever's there — including bugs — and
locks the bug in as the contract. The next person to fix it will have to fight your test.

Concretely, this means:

- **Derive expected values from the contract, not the run.** Work out what the API or
  database is documented to return, what the connector is supposed to transform it into, and
  what the caller relies on. Then write the assertion. If you can't tell what the right
  answer is, ask the user — don't guess from output.
- **When a test fails, the first question is "is the code wrong?", not "is the test wrong?"**
  Trace the value through the layers before changing either. If a connector returns
  `Decimal('50000')` when the spec says it should be `Decimal('50000.00')`, don't just relax
  the assertion — figure out which layer is dropping the precision.
- **Integration bugs hide in transformations.** Watch the boundaries where data changes
  shape: string → `Decimal`, dict → dataclass, raw timestamp → tz-aware `datetime`. Those are
  the shapes bugs hide in.

This applies whether the flow is brand new or pre-existing. Pre-existing flows are *more*
likely to have latent layer-interaction bugs that have never been challenged by a test.

---

## When an integration test earns its keep

From `.claude/rules/testing.md`:

**Write one when:**
- Multi-layer interactions need verifying (connector → service → client; repository → client →
  session)
- Realistic API data flows through domain transformations
- Parameter passing across multiple function calls in different layers
- Error propagation from low-level errors to high-level handlers

**Don't write one for:**
- Simple unit-level logic
- Individual methods in isolation
- Business logic that doesn't span layers

If the user asks for an integration test that doesn't fit the above, push back: explain that
mock-everything-internally tests duplicate the unit suite without catching layer-interaction
bugs. Suggest the unit-test skill or a narrower integration scope.

---

## Pick the scope

If the user named a flow (e.g. "the new `AddOrder` connector", "the Supabase bot run repo
end-to-end"), test that flow.

Otherwise, work from the diff and look for changes that **cross module or layer boundaries**:

```bash
git diff --name-only main...HEAD
git diff main...HEAD -- '*.py'
```

Signals that warrant integration coverage:
- A new connector + the service path it calls
- A new repository method + the client path it uses
- Wiring between two modules (e.g. exchange_connector writing into data_system)
- A new error class that should propagate from a low layer up to a caller

If nothing in the diff crosses a layer, say so and stop — don't invent a reason to write one.

---

## Workflow

1. **Read the full layer stack in scope.** For a connector test: connector + service + client +
   any domain models and exceptions. You can't write a credible integration test from a single
   file.
2. **Find the right test file.** Integration tests are flat under `scalper/tests/integration/`,
   one file per module: `test_{module}_integration.py` for single-module flows, or
   `test_{module_a}_{module_b}_integration.py` for cross-module ones (see existing
   `test_exchange_connector_data_system_integration.py`). Add to the existing file when the
   module already has one; create a new file only for a genuinely new scope.
3. **Read `pytest.ini`** to confirm the integration markers. Top-level `integration` plus the
   module-specific `{module}_integration` are registered there. If you need a new
   `{module}_integration` marker, register it in the same change.
4. **Load `.claude/rules/testing.md`** for the conventions. Don't duplicate it from memory.
5. **Plan the boundaries.** Write down — for yourself — exactly what you'll mock and what you
   won't. The rule: mock at the edge of the system (the HTTP request, the DB session, the
   filesystem), let everything our code owns run for real. Show the user the plan if the
   surface is non-trivial.
6. **Write the tests** matching the patterns in the neighbouring integration file. Import from
   direct module paths.
7. **Run them.**
   ```bash
   pytest -m {module}_integration -v
   pytest -m integration              # full integration suite — confirm no regressions
   ```
   Report pass/fail counts.
8. **Stop and ask** before adding a new top-level test dependency, before a test that would
   make a real network call or hit a real DB, or before changes that touch
   `data_system/schema.sql`.

---

## Boundaries — what to mock, what to let run

The whole point of integration tests is that the layers run together. Get the boundary line
right:

| Mock                                               | Don't mock                                |
|----------------------------------------------------|-------------------------------------------|
| `requests` / the HTTP transport                    | The `KrakenApiClient` itself              |
| The DB session / SQLAlchemy session factory        | Repositories, models, query construction  |
| `time.sleep` (so retry loops don't actually delay) | Retry logic, backoff math                 |
| Filesystem I/O at the edge                         | Domain transformations, validation        |
| The Supabase client's outbound HTTP call           | The `SupabaseClient` wrapper, repos       |

Existing pattern for HTTP-boundary mocking (see `test_exchange_connector_integration.py`):
patch `requests` (or the specific call site), construct realistic raw API payloads as fixtures,
and let the connector → service → client stack run end-to-end.

---

## Common pitfalls

These are repeated almost verbatim from `.claude/rules/testing.md` because they bite every
time:

- **Mock `time.sleep`.** Retry loops will actually sleep otherwise and your test suite hangs.
- **Pagination mocks need a terminating sentinel.** A naive `mock.return_value = next_page`
  loops forever. Return a sequence ending in the empty / final-page response.
- **`isinstance(obj, list)` works; `isinstance(obj, list[Type])` does not.** The parameterised
  form raises at runtime. Use the bare type for runtime checks.
- **Account for service-level transformations** applied before results reach the test (e.g.
  `[:-1]` slicing for pagination cursors, `result['result']` unwrapping). Compare against the
  shape the connector actually returns, not the raw mock payload.
- **Make raw fixtures realistic.** Kraken returns prices as strings, timestamps as floats with
  microseconds, paginated cursors as nanosecond strings. If the fixture is sloppy, the test
  passes against fiction.
- **Money is `Decimal` end-to-end.** A test that constructs expected values as `float` will
  silently disagree with the connector's `Decimal` outputs in confusing ways.

---

## Realistic fixture data

Integration tests live or die by their fixtures. Copy real API response shapes from existing
fixtures in the same module's integration file rather than inventing them — Kraken in
particular has fiddly conventions (string-encoded numbers, ordered tuples instead of objects,
nanosecond cursors) that are easy to get subtly wrong.

For Supabase / Postgres flows, mirror the actual column names and types from
`data_system/schema.sql`. `DECIMAL(32,12)` truncation is documented in the architecture
decision log — fixtures that ignore it produce assertions that don't match production.

---

## Output

After running the tests, report:

```
## Coverage added
- {file}: {N} integration tests covering {brief — e.g. "connector → service → client happy
  path, error propagation from 5xx, pagination termination"}
- ...

## Boundaries mocked
- {what was mocked at the edge, e.g. "requests.request via patch, time.sleep"}

## Test results
{pytest -m {module}_integration summary; pytest -m integration summary}

## Skipped on purpose
{anything in scope that wasn't covered, with the reason — pure unit logic, etc. Empty is
fine.}

## Follow-ups
{e.g. "consider unit tests for the new validation branch in TradesConnector._to_domain".
Empty is fine.}
```

---

## Files in this skill

- `SKILL.md` — this file.

For style/architecture rules (Python 3.12+ syntax, single quotes, British English, type hints,
marker hierarchy, layered architecture), see `CLAUDE.md`, `.claude/rules/testing.md`, and
`.claude/rules/architecture.md`. Read them when working — don't work from memory.
