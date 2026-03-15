---
agent: agent
description: "Manually test the add and get paths for all four Supabase repos and models using query_supabase.py"
---

# Test Supabase Repos

Use the [query_supabase.py](../../scalper/scripts/query_supabase.py) script to manually test the **add** and **get** paths for each of the four repos and models in Supabase.

## Instructions

- The real Supabase tables have not been used for live trading yet, so it is safe to insert whatever test data is needed.
- Cover edge cases thoroughly — test that inserted, fetched, and returned records are **exactly correct**, do not cause errors, and are persisted accurately.
- If useful, also run your own Python scripts or shell commands to inspect the repos, table schemas, dataclasses, or any related behaviour.

## Scope

For each of the four repos and their corresponding models:

1. Test the **add path** — insert representative records, including edge cases (e.g. nulls, boundary values, duplicates if relevant).
2. Test the **get path** — fetch records and assert that what is returned matches exactly what was inserted.
3. Verify **persistence** — confirm data survives a round-trip through the repo layer without mutation or loss.
4. Report any schema mismatches, dataclass issues, or unexpected behaviour encountered along the way.

## Output

Summarise results per repo: which paths passed, which failed, and any issues found.