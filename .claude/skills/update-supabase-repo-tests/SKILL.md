---
name: update-supabase-repo-tests
description: Update scalper/scripts/test_supabase_repos.py after changes to the Supabase repos or models. Use when the user has added/modified methods on SupabaseBotRepository, SupabaseBotRunRepository, SupabaseBotTickRepository, or SupabaseBotOrderRepository, or changed the Bot/BotRun/BotTick/BotOrder models, and wants the manual-verification script kept in sync.
---

# Update Supabase Repo Tests

The script `scalper/scripts/test_supabase_repos.py` exercises the four live-trading Supabase
repos against real Supabase to catch type-serialisation and FK bugs that unit tests can't.
After changes to those repos or their models, this skill brings the script up to date.

> ⚠️ **The script touches real, live-trading data**. Read the script's safety preamble and
> follow the same patterns when extending it: prefix-tagged identifiers, ledger-tracked inserts,
> try/finally cleanup, post-cleanup residue sweep, no unscoped deletes, no truncates.

---

## Workflow

1. **Read** the four repo implementations to find what changed:
   - `scalper/data_system/repositories/bot/supabase_bot_repository.py`
   - `scalper/data_system/repositories/bot_run/supabase_bot_run_repository.py`
   - `scalper/data_system/repositories/bot_tick/supabase_bot_tick_repository.py`
   - `scalper/data_system/repositories/bot_order/supabase_bot_order_repository.py`

2. **Read** the four models in case fields changed:
   - `scalper/data_system/models/bot_model.py`
   - `scalper/data_system/models/bot_run_model.py`
   - `scalper/data_system/models/bot_tick_model.py`
   - `scalper/data_system/models/bot_order_model.py`

3. **Read** the existing script — `scalper/scripts/test_supabase_repos.py` — and identify what
   it currently covers.

4. **Diff** the public methods on each repo against the script's coverage. For any new method,
   add a corresponding test scenario. For removed/renamed methods, update or delete the
   corresponding test.

5. **Diff** the model fields against the test data being constructed. New required fields need
   a sensible test value; new optional fields need at least one test that exercises both `None`
   and a real value.

6. **Update type-round-trip checks** if a new type was introduced (e.g. a new enum, a new
   `Decimal` field). Confirm round-trip preservation — string → DB → string → object — works
   without loss.

---

## Safety patterns the script must keep

These constraints are non-negotiable. Live-trading tables hold thousands of real rows; the
script must not interfere with them and must guarantee zero residue.

- **Test prefix** — every identifier created uses `claudit-test-` plus the per-run UUID. Names,
  bot IDs, exchange order IDs all carry it.
- **Ledger** — every successful bot insert appends the `bot_id` to an in-memory list. Related
  rows (runs, ticks, orders) are reachable for cleanup via that bot_id (FK).
- **`try`/`finally` cleanup** — the finally block deletes all rows scoped to each ledgered
  `bot_id` in reverse FK order: `bot_orders` → `bot_ticks` → `bot_runs` → `bots`. Each delete
  is `.eq('bot_id', ...)`-scoped (or `.eq('id', ...)` for `bots`), regardless of test outcome.
- **Residue sweep** after cleanup — re-query each table for the prefix; if anything remains,
  retry delete; if still anything remains, exit non-zero with the IDs.
- **Pre-flight** — query for the prefix before inserting; refuse to start (or prompt to clean
  up) if leftover residue exists.
- **Confirmation** — print the target Supabase URL and require interactive `yes` (skippable
  with `--yes` for repeat use).
- **No unscoped deletes** — every `.delete()` call is `.eq('id', specific_id)` or
  `.like('field', 'claudit-test-%')`. Never bare `.delete()`.
- **No truncate, no schema operations** — ever.

When extending the script, copy these patterns; do not invent new cleanup paths that bypass
them.

---

## Output

After updating the script, summarise:

- New scenarios added (per repo, per method)
- Removed scenarios (and why)
- Any new type-round-trip checks
- Any safety-pattern changes (should be very rare)

Then suggest the user runs the script: `uv run python scalper/scripts/test_supabase_repos.py`.
