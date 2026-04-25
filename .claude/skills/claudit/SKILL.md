---
name: claudit
description: Audit CLAUDE.md, .claude/rules/, .claude/skills/, and .github/copilot-instructions.md against the actual state of the codebase. Use when the user asks to "claudit", check whether docs are stale, or sync instructions with the code. Good "leftover tokens" task at the end of a session.
---

# Claudit — Instruction Drift Audit

Scan the codebase and compare it against the project's instruction, rules, and skill files to
find anything that's stale, missing, or incorrect.

> ⚠️ **Audit only.** Don't edit any files until the user confirms the proposed changes.

---

## Files to review

- `CLAUDE.md`
- `.claude/rules/testing.md`
- `.claude/rules/architecture.md`
- `.claude/rules/docstrings.md`
- `.claude/skills/code-review/SKILL.md`
- `.claude/skills/add-strategy/SKILL.md`
- `.claude/skills/update-supabase-repo-tests/SKILL.md`
- `.github/copilot-instructions.md`

(Add any new rules or skills that have been created since this list was written.)

---

## Checks

For each finding, note the specific file, the section, and the proposed fix.

### 1. Project structure (CLAUDE.md)
- List the actual top-level directories under `scalper/`.
- Compare against the structure tree in CLAUDE.md.
- Flag new modules, renamed directories, and removed directories.

### 2. Useful entry points (CLAUDE.md)
- `ls scalper/scripts/` — list every `.py` script.
- Compare against the entry-points section of CLAUDE.md.
- Flag scripts that exist but aren't listed, or listed but missing.

### 3. Code conventions (CLAUDE.md "Code Conventions")
- Spot-check recent commits (`git log --oneline -20`) for code style. The conventions section
  says one thing — does the code on `main` actually match?
- Flag any rule that's stated in CLAUDE.md but consistently broken in the repo, or any
  consistent pattern in the code that isn't captured in CLAUDE.md or the rules.

### 4. Pytest markers
- `cat pytest.ini` — list all registered markers.
- Check whether CLAUDE.md, the rules files, or any skill references markers that no longer
  exist.
- Flag significant new modules in `pytest.ini` that aren't documented anywhere.

### 5. Rules files (`.claude/rules/`)
- For each rules file, check that the patterns it describes still exist in the code:
  - `architecture.md` — repository pattern paths, layered architecture in
    `exchange_connector/`, dual-implementation pattern in `strategy_manager/`.
  - `testing.md` — test directory structure, marker conventions.
  - `docstrings.md` — docstring style on existing public APIs.
- Flag rules that no longer reflect reality, or new patterns that should be documented.

### 6. Skills (`.claude/skills/`)
- For each `SKILL.md`, check that referenced files, paths, and class/function names still exist.
  - `add-strategy/SKILL.md` — paths in `strategy_manager/`, indicators/rules listed.
  - `update-supabase-repo-tests/SKILL.md` — repo paths under
    `data_system/repositories/{bot,bot_order,bot_run,bot_tick}/`.
  - `code-review/SKILL.md` — references to rules files.
- Flag any skill referencing dead paths or classes.

### 7. Supabase repo coverage (`update-supabase-repo-tests` boundary)
- List the public methods on each of `SupabaseBotRepository`, `SupabaseBotRunRepository`,
  `SupabaseBotTickRepository`, `SupabaseBotOrderRepository`.
- Compare against the methods exercised in `scalper/scripts/test_supabase_repos.py`.
- Flag any repo method not covered by the script.

### 8. `.github/copilot-instructions.md`
- Confirm it still mirrors CLAUDE.md + `.claude/rules/`. If it has drifted significantly, flag
  the divergences.
- The source of truth is CLAUDE.md and rules; copilot-instructions tracks them.

### 9. `.github/prompts/`
- List the actual files in `.github/prompts/`.
- The only Copilot-era prompt that should remain is
  `plan-tradeExecutorLiveTrading.prompt.md` (kept for reference until live trading is fully
  shipped). Flag anything else that's reappeared.

### 10. Stale examples
- Scan code examples in CLAUDE.md, rules, and skills for references to specific class names,
  file paths, or module structures that no longer exist.
- Flag anything that would mislead an agent working in the current codebase.

---

## Output

```
## Summary
{X issues found across Y files}

## Proposed changes
| File | Section | Current | Proposed fix |
|------|---------|---------|--------------|
| ...  |   ...   |   ...   |     ...      |

## New conventions worth capturing
{patterns the code uses consistently but which aren't documented anywhere — could go into
CLAUDE.md or a rules file. Empty section is fine.}

## New skills worth creating
{repeatable workflows that have surfaced and don't have a skill yet. Empty section is fine.}
```

After the user reviews and confirms, apply the approved changes.
