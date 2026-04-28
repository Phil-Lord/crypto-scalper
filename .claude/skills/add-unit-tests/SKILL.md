---
name: add-unit-tests
description: Add or update unit tests in scalper/tests/unit/ to cover new or changed functionality. Use when the user asks to "add tests", "write unit tests", "cover this", "test this module", or after they've made code changes that need test coverage. Works from the working-tree diff by default, or from a file/module the user names. Push back on happy-path-only requests and auto-add live-vs-vectorised parity tests for dual-implementation classes. For integration tests, this is the wrong skill.
---

# Add Unit Tests

Add or update unit tests in `scalper/tests/unit/` for new or changed code.

> Scope: **unit tests only.** Integration tests live in `scalper/tests/integration/` and follow
> different conventions (mock-only-at-boundaries, multi-layer flows). If the change genuinely
> spans layers, flag that to the user and stop — they should run a separate pass for integration
> coverage.

---

## Tests are a spec, not a snapshot

The job is to test what the code is **supposed** to do, then check it does that. Not to test
what the code **currently** does and call it covered.

The failure mode to avoid: run the function, observe the output, paste it into an `assert`.
That builds a regression net for whatever's there — including bugs — and locks the bug in as
the contract. The next person to fix it will have to fight your test.

Concretely, this means:

- **Derive expected values from the spec, not the run.** Read the source, the docstring, and
  any usage at call sites. Work out what the right answer is, *then* write the assertion. If
  you can't tell what the right answer is, ask the user — don't guess from output.
- **When a test fails, the first question is "is the code wrong?", not "is the test wrong?"**
  Read the source against the test's intent before changing either. If the code is wrong, fix
  the code. If the spec is ambiguous, surface that to the user.
- **Be especially suspicious of round numbers, off-by-one outputs, and "weird but it returns
  this" cases.** Those are the shapes bugs hide in. If the code returns `[1, 2, 3, 4]` when
  you expected `[1, 2, 3, 4, 5]`, don't just assert four — figure out why.

This applies whether the code is brand new or pre-existing. Pre-existing code is *more*
likely to have latent bugs that have never been challenged by a test.

---

## Pick the scope

If the user named a file or module (e.g. `scalper/data_system/repositories/bot/`), test that.

Otherwise, work from the diff:

```bash
git diff --name-only main...HEAD       # files changed on this branch
git diff --name-only                   # uncommitted changes
git diff main...HEAD -- '*.py'         # actual changes (read this to see what's new)
```

Filter to production code under `scalper/` — ignore `scalper/scripts/` (entry points, not
unit-tested), `scalper/tests/`, docs, and config files. If nothing meaningful is in scope, ask
the user what they want covered.

---

## Workflow

1. **Read the source in scope.** Understand what each new/changed function or class does, what
   its inputs and outputs are, and what could go wrong (validation, branching, error paths,
   boundary conditions).
2. **Locate or create the test file.** Tests mirror source paths:
   `scalper/strategy_manager/foo.py` → `scalper/tests/unit/strategy_manager/test_foo.py`. If the
   test file exists, read it — match its fixtures, marker style, and naming. If it doesn't
   exist, create it.
3. **Read `pytest.ini`** to see existing markers. Any new marker the test file needs (a new
   class marker, a new sub-category) must be registered there in the same change.
4. **Load `.claude/rules/testing.md`** for the conventions (naming, Given/When/Then, marker
   hierarchy, fixtures). Don't duplicate that file's contents in the skill — read it when
   working.
5. **Plan coverage** before writing. For each unit in scope, list the behaviours worth testing
   (see "Coverage" below). Show the user the plan if it's non-trivial — five-line helpers don't
   need a plan, a new repository or strategy does.
6. **Write the tests.** Match existing patterns in the neighbouring test files. Import from the
   direct module path (`from data_system.models.bot_tick_model import BotTick`), not the package
   re-export.
7. **Run them.**
   ```bash
   pytest scalper/tests/unit/{path}/test_{module}.py -v
   ```
   Then a quick `pytest -m {module}` to confirm nothing regressed in the wider module. Report
   pass/fail counts.
8. **Stop and ask** before introducing a new test dependency, modifying `pytest.ini` markers
   beyond simple registration, or touching tests outside the scope.

---

## Coverage — what to test

Test behaviour, not paths. The bar is: would this test catch a real bug?

**Cover:**
- Validation and error paths — what happens with bad input, missing fields, wrong types
- Branching logic — each meaningful branch, including the "nothing to do" case
- Boundary conditions — empty inputs, single-element inputs, exact-threshold values, off-by-one
- State transitions — for stateful classes, the sequence that exposes the state, not just one
  call
- Frozen dataclasses — at minimum, a `pytest.raises(AttributeError)` on assignment to confirm
  immutability, plus that required fields are required

**Skip:**
- Pure delegation (a method that just calls another with the same arguments and no
  transformation) — testing it adds noise without catching bugs
- Trivial getters, constants, and re-exports
- Framework behaviour (don't test that `@dataclass(frozen=True)` works, test that *your* model
  uses it correctly)

**Push back if the user asks for happy-path-only.** Project rule (`.claude/rules/testing.md`):
"Test behaviour, not just code paths. ❌ Happy-path-only tests with everything mocked." Say so,
suggest the missing edge cases, and let them decide. Don't silently produce shallow tests.

---

## Special cases

### Dual-implementation classes (strategies and indicators)

If the class in scope has **both** a stateful live implementation (`update`,
`_generate_signal`) **and** a vectorised one (`compute`, `_generate_signals`), add a parity
test that runs both on the same input data and asserts identical output. This is required by
`.claude/rules/architecture.md` — any logic change must keep the two paths in sync, and the
test is what enforces it.

Pattern:

```python
def test_live_and_vectorised_match_on_same_data(self, sample_ohlc_df):
    # Given
    live = MyIndicator(window=14)
    live_results = [live.update(row.close) for row in sample_ohlc_df.itertuples()]

    # When
    vectorised_results = MyIndicator.compute(sample_ohlc_df, window=14)

    # Then
    # Compare ignoring the warm-up Nones from the live path
    assert vectorised_results.tolist()[14:] == live_results[14:]
```

Adjust the comparison to the actual return shapes — the point is one test, same data, both
paths.

### Repositories

For a new method on a `{Backend}{Entity}Repository`, follow the existing tests in the same
folder. Mock the client (`SQLAlchemyClient` / `SupabaseClient`) and the session — don't hit a
real database. Cover at minimum: the happy path, the not-found / empty-result case, and any
error-translation the repository does.

### Connectors

Mock the underlying service. Cover the domain transformation (raw API shape → domain object)
including malformed-input validation, since connectors are a boundary layer
(`.claude/rules/architecture.md`: "Validate at boundaries where external data enters").

### Money and time

`Decimal` for live-trading money, `datetime` timezone-aware UTC. Tests should construct values
the same way — don't pass `float` to a `Decimal` field in a test fixture, it masks bugs.

---

## Output

After running the tests, report:

```
## Coverage added
- {file}: {N} tests covering {brief — e.g. "validation, retry, empty-input"}
- ...

## Test results
{pytest summary}

## Skipped on purpose
{anything in scope that wasn't tested, with the reason — pure delegation, etc. Empty is fine.}

## Follow-ups
{e.g. "this change spans connector → service → client; consider an integration test." Empty is
fine.}
```

---

## Files in this skill

- `SKILL.md` — this file.

For style/architecture rules (Python 3.12+ syntax, single quotes, British English, type hints,
marker hierarchy, dual-implementation pattern), see `CLAUDE.md`,
`.claude/rules/testing.md`, and `.claude/rules/architecture.md`. Read them when working — don't
work from memory.
