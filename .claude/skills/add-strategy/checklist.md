# Add-Strategy Checklist

Work through this top to bottom. Each step has its own acceptance criteria — don't tick a step
until those criteria are met.

---

## 1. Scaffold the config

- [ ] File at `scalper/strategy_manager/strategies/{name}_strategy_config.py`
- [ ] `@dataclass(frozen=True)` with required fields first, defaulted fields last
- [ ] All attributes documented in the class docstring (see `.claude/rules/docstrings.md`)
- [ ] `__post_init__` validates every constraint (e.g. `short_window < long_window`,
      `oversold < overbought`) with a clear `ValueError` message

Template: see "Strategy config" in `templates.md`.

## 2. Reuse or create indicators

- [ ] Check `scalper/strategy_manager/indicators/` first — reuse if one fits
- [ ] If creating a new one: file at `scalper/strategy_manager/indicators/{name}_indicator.py`
- [ ] Subclass `Indicator` and implement **both** `update` (live) and `compute_vectorised`
- [ ] State is bounded — use `deque(maxlen=window)`, never an unbounded `list`
- [ ] `reset()` restores the indicator to its post-`__init__` state
- [ ] Exported from `strategy_manager/indicators/__init__.py`

## 3. Reuse or create rules

- [ ] Check `scalper/strategy_manager/rules/` first — reuse if one fits
- [ ] If creating a new one: file at `scalper/strategy_manager/rules/{name}_rule.py`
- [ ] Subclass `Rule` and implement **both** `check` (live) and `compute_vectorised`
- [ ] Live and vectorised paths return identical signals on identical inputs
- [ ] Exported from `strategy_manager/rules/__init__.py`

## 4. Create the strategy

- [ ] File at `scalper/strategy_manager/strategies/{name}_strategy.py`
- [ ] Subclass `Strategy`; register indicators and rules in `__init__`
- [ ] Implement `_generate_signal(rule_results)` — live, called once per OHLC bar
- [ ] Implement `_generate_signals(results)` — vectorised, called with a full DataFrame
- [ ] Both methods return identical signals on identical data
- [ ] `warmup_candles` reflects the indicator with the longest warmup, plus rule lookback

Template: see "Strategy class" in `templates.md`.

## 5. Register in the factory

- [ ] Add `'{Name}Strategy': ({Name}Strategy, {Name}StrategyConfig)` to the `STRATEGIES` dict
      in `scalper/strategy_manager/factory.py`
- [ ] Import the strategy and config at the top of `factory.py`

## 6. Update exports

- [ ] Add the strategy and config to `scalper/strategy_manager/strategies/__init__.py`
- [ ] Add anything externally consumable to `scalper/strategy_manager/__init__.py`

## 7. Add backtesting param sets

- [ ] Add a param dict to `scalper/utils/strategy_configs.py` so the strategy can be backtested
      and optimised via the standard scripts

## 8. Write tests

- [ ] `scalper/tests/unit/strategy_manager/strategies/test_{name}_strategy.py`
- [ ] If new indicator: `scalper/tests/unit/strategy_manager/indicators/test_{name}_indicator.py`
- [ ] If new rule: `scalper/tests/unit/strategy_manager/rules/test_{name}_rule.py`
- [ ] Cover: config validation edge cases (each `ValueError`), indicator output, signal
      generation for BUY/SELL/HOLD
- [ ] Include a parity test: run `_generate_signal` and `_generate_signals` on the same data
      and assert identical output

Template: see "Strategy unit tests" in `templates.md`.

## 9. Register pytest markers

- [ ] Add new markers to `pytest.ini` at module / category / class level (see
      `.claude/rules/testing.md` for the hierarchy)
- [ ] Existing markers like `strategy_manager`, `strategies`, `indicators`, `rules` are reused —
      only register the new class-level marker (e.g. `{name}_strategy`)

## 10. Update docs

- [ ] `docs/strategy_manager/` mentions the new strategy in the relevant page

---

## Final acceptance

- [ ] `pytest -m {name}_strategy` passes
- [ ] `pytest -m strategy_manager` still passes (no regression)
- [ ] No `Optional`, `Union`, `List`, `Dict` from `typing` introduced
- [ ] Single quotes throughout, British English in identifiers and prose
- [ ] No unbounded state in any new indicator
