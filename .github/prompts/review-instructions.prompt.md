# Review Instructions

> ⚠️ **Do NOT edit any files yet.** Audit only. Report proposed changes and wait for confirmation.

Scan the codebase and compare it against the project's instruction and prompt files to find anything
that is stale, missing, or incorrect. Run this periodically to keep documentation in sync with the
code.

---

## Files to Review

- `CLAUDE.md`
- `.github/copilot-instructions.md`
- `.github/prompts/audit-module.prompt.md`
- `.github/prompts/new-module.prompt.md`
- `.github/prompts/add-strategy.prompt.md`
- `.github/prompts/new-feature.prompt.md`

---

## Instructions

Work through each check category below. For each finding, note the specific file and proposed fix.

### 1. Project Structure (CLAUDE.md)

- List the actual top-level directories under `scalper/`
- Compare against the structure tree in CLAUDE.md
- Flag any new modules, renamed directories, or removed directories

### 2. Makefile Targets (CLAUDE.md)

- Read `scalper/Makefile` — list all `test/...` targets
- Compare against the example commands in CLAUDE.md `## Key Commands`
- Flag targets that exist in the Makefile but are absent from CLAUDE.md examples (or vice versa if
  CLAUDE.md documents targetswd that don't exist)

### 3. Module Overview (copilot-instructions.md)

- Check the `## Project Overview` module list
- Confirm each listed module still exists and its description is accurate
- Flag any new modules under `scalper/` not mentioned in the overview

### 4. Strategies (add-strategy.prompt.md)

- List the actual files in `scalper/strategy_manager/strategies/`
- List the actual files in `scalper/strategy_manager/indicators/`
- List the actual files in `scalper/strategy_manager/rules/`
- Compare against the "Existing Indicators & Rules" section of `add-strategy.prompt.md`
- Flag any new indicators or rules that should be added to that list

### 5. Pytest Markers (CLAUDE.md + audit prompt)

- Read `pytest.ini` — list all registered markers
- Check whether `CLAUDE.md` or the audit prompt reference any markers that no longer exist
- Flag any significant new modules in `pytest.ini` that are undocumented

### 6. Prompts List (copilot-instructions.md + CLAUDE.md)

- List the actual files in `.github/prompts/`
- Compare against the prompt listings in copilot-instructions.md (Prompt Files section) and CLAUDE.md
  (Adding New Things section)
- Flag any prompt files that exist but aren't listed, or that are listed but don't exist

### 7. Patterns in the Codebase

Skim recent source files for patterns that are used consistently but not documented in the
instructions. Look for:
- New architectural patterns or conventions not covered in Part 2 of copilot-instructions.md
- New config classes, base classes, or abstractions that have emerged
- Any helper utilities in `utils/` not mentioned anywhere in the instructions

### 8. Stale Examples

- Scan code examples in copilot-instructions.md for references to specific class names, file paths,
  or module structures that no longer exist
- Flag anything that would mislead an agent working in the current codebase

---

## Output Format

Provide a single report with:

1. **Summary** — One sentence: "X issues found across Y files"
2. **Proposed changes** — Table with columns: `File | Section | Current text (brief) | Proposed fix`
3. **New prompt suggestions** — Any repeatable tasks discovered that don't have a prompt yet

After confirmation, apply all approved changes.
