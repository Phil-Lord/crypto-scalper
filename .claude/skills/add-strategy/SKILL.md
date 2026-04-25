---
name: add-strategy
description: Add a new trading strategy to scalper/strategy_manager/. Use when the user wants to introduce a new strategy, indicator, or rule, or asks to "add a strategy" or scaffold a strategy. Walks the standard add-strategy workflow - config → indicators → rules → strategy class → factory registration → tests.
---

# Add Strategy

Add a new trading strategy to `scalper/strategy_manager/`. Reuse existing indicators and rules
where possible; only create new ones if the strategy genuinely needs them.

---

## What this skill produces

```
scalper/strategy_manager/
├── strategies/
│   ├── {name}_strategy.py
│   ├── {name}_strategy_config.py
│   └── __init__.py                 # add exports here
├── indicators/
│   └── {name}_indicator.py         # only if new
├── rules/
│   └── {name}_rule.py              # only if new
└── factory.py                      # register strategy here

scalper/tests/unit/strategy_manager/
├── strategies/test_{name}_strategy.py
├── indicators/test_{name}_indicator.py   # only if new
└── rules/test_{name}_rule.py             # only if new
```

Plus updates to `pytest.ini` (markers), `scalper/utils/strategy_configs.py` (param sets), and
`docs/strategy_manager/`.

---

## How to use this skill

1. **Clarify requirements first.** Confirm strategy name, which indicators/rules it needs, what
   parameters it takes, and its entry/exit conditions. Ask before scaffolding.
2. **Check what already exists** before creating new indicators or rules:

   ```bash
   ls scalper/strategy_manager/indicators
   ls scalper/strategy_manager/rules
   ```

3. **Walk `checklist.md`** in order. It is the source of truth for the workflow, file paths, and
   acceptance criteria. Tick each box as you go — don't skip ahead.
4. **Use `templates.md` as scaffolding.** It contains three labelled code blocks (config,
   strategy, tests). Copy the relevant block, then replace every `{{placeholder}}` with the new
   strategy's specifics. The templates encode the patterns (frozen dataclass,
   `_generate_signal` + `_generate_signals`, marker hierarchy) so you don't have to reconstruct
   them from prose.
5. **Stop and ask** before doing anything that requires user judgement: introducing a new
   dependency, changing a public API in `strategy_manager/__init__.py`, or modifying
   `data_system/schema.sql`.

---

## Files in this skill

- `SKILL.md` — this file (overview + how to use).
- `checklist.md` — the actual workflow, file paths, and acceptance criteria.
- `templates.md` — copy-paste scaffolds for the strategy class, config, and tests.

For style/architecture rules (frozen dataclasses, type hints, British English, test naming,
marker hierarchy, dual-implementation pattern), see `CLAUDE.md`,
`.claude/rules/architecture.md`, and `.claude/rules/testing.md`.
