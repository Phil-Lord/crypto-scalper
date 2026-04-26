---
name: audit-docs
description: Audit the mkdocs site under `docs/` against the actual code and apply fixes. Use whenever the user asks to "audit the docs", "check the docs", "update the docs after change X", "make sure the docs are still accurate", or worries about doc drift. Also covers checking that non-obvious architectural decisions are recorded in `docs/architecture-decision-log.md`. Two modes — full sweep across all module docs, or a targeted pass focused on a specific module or recent code change.
---

# Audit Docs — Keep `docs/` Honest

The `docs/` site documents the design, architecture, and operational workflows of each module
under `scalper/`. It drifts whenever code changes without a paired doc edit. This skill compares
docs against the current code and applies fixes directly, so the user can review the diff.

> **Auto-fix.** Apply the changes you propose. The user reviews the resulting diff. No
> "summary first, edits later" two-step — that wastes a turn. Still pause and ask before
> deleting whole sections, restructuring a page, or rewriting more than ~30% of a doc.

> **Skim before editing.** Read the doc fully before changing it. Many statements are
> deliberately abstract to age well — don't "fix" them by pinning them to a specific class name
> just because the abstract phrasing didn't match a grep.

---

## Mode selection

Pick a mode from the user's request:

- **Targeted** — the user names a module, file, or recent change ("I just added X to
  `strategy_manager`, update the docs"). Scope the audit to the affected module's docs +
  the ADL.
- **Full sweep** — the user asks broadly ("audit the docs", "check nothing is stale"). Walk
  every section listed in `mkdocs.yml`'s `nav`.

When in doubt, ask once. Targeted is much cheaper.

---

## Module-to-docs map

Each top-level module has a docs section. Use this map to scope work:

| Code module                       | Docs section                        |
| --------------------------------- | ----------------------------------- |
| `scalper/data_system/`            | `docs/data-system/`                 |
| `scalper/exchange_connector/`     | `docs/exchange-connector/`          |
| `scalper/strategy_manager/`       | `docs/strategy-manager/`            |
| `scalper/backtesting_engine/`     | `docs/backtesting-engine/`          |
| `scalper/trade_executor/`         | `docs/trade-executor/`              |
| Fly.io / Supabase deployment      | `docs/cloud-architecture.md`        |
| Cross-module decisions            | `docs/architecture-decision-log.md` |
| Landing page                      | `docs/index.md`                     |

Modules **without** a docs section right now: `core/`, `study_analyser/`, `ui/`, `utils/`,
`scripts/`. Treat that as intentional — don't propose new sections unless the user asks.

`mkdocs.yml`'s `nav` is the source of truth for what's published. If you add or remove a doc
file, update `nav` in the same change.

---

## What to check

For each in-scope doc, work through these checks. Skip ones that don't apply.

### 1. Code references still exist

Grep for every class, function, file path, script name, env var, and config attribute
mentioned in the doc. Anything that no longer exists is stale.

Common offenders:
- Renamed classes (`IntervalContext` → removed; `BalanceSizer` → `AllInPositionSizer`).
- Moved files (a class moved between `services/` and `connectors/`).
- Scripts under `scalper/scripts/` that were renamed or deleted.
- Re-exports from `__init__.py` — if the doc says "import from `data_system`", check
  `scalper/data_system/__init__.py` actually re-exports it.

### 2. Architecture descriptions match the code

The patterns in `.claude/rules/architecture.md` (repository, layered Client/Service/Connector,
dual live+vectorised, etc.) are also reflected in the docs. When the code changes shape, the
docs need to follow.

- Layer boundaries — did a method drift from connector to service or vice versa?
- New repository implementations or backends not mentioned in `data-system/backends.md`.
- Public API on a module's `__init__.py` vs. what `index.md` claims is exported.

### 3. Schema reference is in sync

`docs/data-system/schema-reference.md` describes the tables and columns. Diff it against
`scalper/data_system/schema.sql`. New columns, renamed tables, changed types, new indexes —
all should be reflected.

Don't propose schema changes here — this is doc drift, not code drift.

### 4. Strategy / indicator / rule inventories

`docs/strategy-manager/reference.md` lists built-in indicators, rules, and strategies. Compare
against `scalper/strategy_manager/{indicators,rules,strategies}/` and the registry in
`factory.py`. Add new ones, remove deleted ones, update parameter tables when configs change.

### 5. Kraken endpoint list

`docs/exchange-connector/api-reference.md` documents each connector. Compare against
`scalper/exchange_connector/connectors/` and the public exports.

### 6. Operational workflows

`docs/trade-executor/operations.md` and `docs/backtesting-engine/parameter-optimisation.md`
describe step-by-step workflows. Walk them against the actual scripts in
`scalper/scripts/` — flag steps that reference removed flags, renamed scripts, or scripts whose
CLI signature has changed.

### 7. Code blocks compile

Open every fenced code block in the in-scope docs. Class names, attribute names, and import
paths must still resolve. Inline examples rot fastest.

Be careful of dangerous code blocks in the operations docs — e.g. anything invoking
`start_scalping.py` or otherwise placing real orders. Verify by **reading** the corresponding
file under `scalper/scripts/`; never execute the block to check it.

### 8. ADL coverage

Two passes:

- **Code → ADL.** Look for patterns in the code that scream "non-obvious decision":
  - Frozen dataclasses with unusual constraints (composite keys, custom metaclasses).
  - Abstract base classes with one implementation (someone designed for plurality — why?).
  - Unusual library configuration (`misfire_grace_time=1`, `max_instances=1`,
    `jitter=3` — exactly the kind of magic numbers the ADL captures).
  - Comments containing "because", "to avoid", "would otherwise" — these are smoke for
    decisions that should be in the ADL instead of buried in code.
  - Workarounds for external systems (PostgreSQL, PostgREST, Kraken quirks).

  For each, check whether the ADL already mentions it. If not, propose an entry.

- **Commits → ADL.** `git log --oneline -30` for recent architectural-shaped commits (refactors,
  abstractions added/removed, schema changes, library version pins). Cross-reference the ADL
  for each. The ADL should cover anything where future-you would ask "why did I do it this
  way?" — not every commit, just the load-bearing ones.

The ADL is grouped by module (`System-wide`, `Data System`, `Trade Executor`, …). Add new rows
to the right table. New module → new heading.

---

## How to apply fixes

1. **Investigate, then edit.** For each finding, confirm it with at least one tool call (Read,
   Grep, Glob) before changing the doc. Don't fix from memory.
2. **Edit small.** Prefer narrow `Edit` calls over rewriting whole sections. Diffs review better.
3. **Preserve voice.** The docs use British English (`optimise`, `analyse`, `serialise`),
   single-sentence explanations, mkdocs-flavour markdown with `admonition` and code fences.
   Match the surrounding style. Don't reflow paragraphs that aren't being changed.
4. **Group related edits.** If the same rename touches three docs, do all three before moving
   on — easier for the user to review as a coherent change.
5. **Update `mkdocs.yml`** if you add/remove/rename a doc file. The `nav` block is ordered;
   new pages slot in alphabetically within their module unless an existing page sets a clear
   ordering.

---

## What to leave alone

- **Existing prose tone.** Don't rewrite passages that are still accurate just because you'd
  phrase them differently.
- **Deliberately abstract statements.** "Repositories own both serialisation directions" is a
  pattern statement, not a class reference — don't pin it to a specific repo.
- **Empty or placeholder pages** the user might be mid-drafting. If a page is conspicuously
  thin (the user just opened it), confirm before editing.
- **The `legacy/` tree.** Not documented; not in scope.

---

## Output

After the audit + fixes are applied, post a short summary:

```
## Audit summary
- Mode: {full sweep | targeted: <scope>}
- Files changed: N

## Changes applied
| File | What changed |
|------|--------------|
| docs/data-system/schema-reference.md | Added `bot_runs.completed_at` column row |
| docs/architecture-decision-log.md    | New ADL entry: APScheduler `misfire_grace_time=1` |
| ...  | ... |

## ADL candidates not added
{Decisions you noticed but weren't sure were ADL-worthy. Empty section is fine — only list
items where you genuinely want the user's call.}

## Open questions
{Anything you couldn't resolve and want the user to decide. Empty section is fine.}
```

The user will read the diff to verify. End by suggesting `mkdocs serve` if the changes were
substantial enough to warrant a visual check.
