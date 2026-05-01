---
name: code-review
description: Audit a module or recent changes against this project's conventions. Use when the user asks to "review", "audit", or "check" code in this repo, or to verify a feature is ready to ship. Distinct from the built-in /review skill (which is PR-focused) — this one audits local code or working-tree diffs against the project's style, testing, architecture, and docstring rules.
---

# Code Review

Audit code in `crypto-scalper` against project conventions.

> ⚠️ **Audit only.** Do not fix anything during the review. Report findings, then wait for the
> user's confirmation before making changes.

---

## Pick the scope

If the user named a module (e.g. `scalper/data_system/`), audit that module.

Otherwise, audit recent changes:

```bash
git diff --name-only main...HEAD       # files changed on this branch
git diff --name-only                   # uncommitted changes
```

If neither is meaningful, ask the user what scope they want.

---

## Workflow

1. **Read** the source files in scope, plus their corresponding unit tests
   (`scalper/tests/unit/{module}/`) and any integration tests under `scalper/tests/integration/`.
2. **Read** `pytest.ini` to confirm any new markers used in the code are registered.
3. **Run the tests** for the scope:
   ```bash
   pytest -m {module}                              # whole module
   pytest scalper/tests/unit/{module}/             # by directory
   pytest <specific files>                         # for a small change
   ```
   Capture pass/fail counts.
4. **Load the relevant rules files** from `.claude/rules/`:
   - `testing.md` for any test changes
   - `architecture.md` if the change introduces a new module, layer, repository, or
     long-running stateful class
   - `docstrings.md` for new public APIs or domain models
5. **Walk the checklist below** against the code. Note specific file/line references for each
   issue.

---

## Checklist

### Universal style (CLAUDE.md)
- [ ] Python 3.12+ syntax (`str | None`, `list[T]`) — no `Optional`/`Union`/`List`/`Dict`
- [ ] Single quotes throughout, including docstrings
- [ ] 100-character line limit
- [ ] British English (optimise, analyse, serialise, summarise)
- [ ] Type hints on all public function/method signatures
- [ ] Imports ordered: stdlib → third-party → local, separated by blank lines, no unused imports
- [ ] No `logging.basicConfig()` outside `scripts/`

### Models & data
- [ ] Domain models are `@dataclass(frozen=True)`
- [ ] Required fields first, defaulted fields last
- [ ] `field(default_factory=...)` for mutable defaults — no bare `[]` or `{}`
- [ ] String-compatible enums (`class Foo(str, Enum)`) for serialised values
- [ ] Enums in type hints rather than `str` for fixed value sets
- [ ] `Decimal` for live-trading money; `float` only for stats/timestamps
- [ ] Datetimes are timezone-aware UTC

### Tests (load `.claude/rules/testing.md`)
- [ ] File/class/method naming follows `test_{action}_{condition}_{expectation}`
- [ ] Given/When/Then comments where structure benefits from them
- [ ] Hierarchical markers applied (module + category + class) and registered in `pytest.ini`
- [ ] Tests cover non-trivial behaviour (retry, error propagation, edge cases) — not happy path
      only
- [ ] Integration tests mock only system boundaries; let internal layers run together
- [ ] For dual-implementation classes, a test runs both live and vectorised paths on the same
      data

### Architecture (load `.claude/rules/architecture.md`)
- [ ] `__init__.py` exports the public API and only the public API
- [ ] Dependencies are injected, not instantiated internally
- [ ] Repository pattern: abstract base + `{Backend}{Entity}Repository` naming
- [ ] Layered modules: client/service/connector responsibilities respected, errors handled in
      the right layer
- [ ] Validation at boundaries where external data enters
- [ ] Long-running stateful classes use `deque(maxlen=N)` or equivalent — no unbounded growth

### Docstrings (load `.claude/rules/docstrings.md`)
- [ ] Domain models document every attribute
- [ ] Public APIs have docstrings; trivial helpers don't
- [ ] reStructuredText style (`:param`, `:return:`)
- [ ] Module under `/docs/{module}/` if the module is significant

### Architecture Decision Log
- [ ] Any non-obvious architectural decision in this scope is captured in
      `/docs/architecture-decision-log.md`

---

## Output format

```
## Test results
{pytest summary — passed / failed / errored}

## What's aligned
{1–3 sentences on the things that follow conventions}

## Issues
| File | Line | Issue | Severity        |
|------|------|-------|-----------------|
| ...  | ...  | ...   | High/Medium/Low |

## Recommendations
{any patterns worth pulling into CLAUDE.md or .claude/rules/, or new prompts/skills the user
might want. Empty section is fine.}
```

After the user reviews and confirms, apply the fixes.
