---
name: add-strategy
description: Add a new trading strategy to scalper/strategy_manager/. Use when the user wants to introduce a new strategy, indicator, or rule, or asks to "add a strategy" or scaffold a strategy. Walks the standard add-strategy workflow - config → indicators → rules → strategy class → factory registration → tests.
---

# Add Strategy

Add a new trading strategy to `scalper/strategy_manager/`. Reuse existing indicators and rules
where possible; only create new ones if the strategy genuinely needs them.

---

## Workflow

1. **Clarify requirements** — Confirm strategy name, what indicators/rules it needs, what
   parameters it takes, what its entry/exit conditions are. Ask before scaffolding.
2. **Create the config** — Frozen dataclass with `__post_init__` validation.
3. **Create indicators** — Only if a new one is genuinely needed; otherwise reuse.
4. **Create rules** — Only if a new one is genuinely needed; otherwise reuse.
5. **Create the strategy** — Subclass `Strategy`, register indicators and rules in `__init__`.
6. **Register in factory** — Add to `STRATEGIES` dict in
   `scalper/strategy_manager/factory.py`.
7. **Update exports** — Add to `strategies/__init__.py` and `strategy_manager/__init__.py`.
8. **Add strategy param configs** - Add param dicts to `scalper/utils/strategy_configs.py`.
9. **Write tests** — Unit tests for config validation, indicator logic, signal generation. Plus
   a test that runs `_generate_signal` and `_generate_signals` on the same data and asserts
   identical output.
10. **Register markers** — Add module/category/class markers to `pytest.ini`.
11. **Update strategy_manager docs** — `docs/strategy_manager/` should mention the new strategy.

---

## File locations

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
├── indicators/test_{name}_indicator.py
└── rules/test_{name}_rule.py
```

---

## Strategy pattern — both implementations

Every strategy implements **both** `_generate_signal` (live, called once per OHLC bar) and
`_generate_signals` (vectorised, called with a full DataFrame for backtesting). Both must
produce identical signals for identical data.

```python
class MyStrategy(Strategy):
    def __init__(self, config: MyStrategyConfig):
        super().__init__()
        self.config = config
        self.register_indicator('my_indicator', MyIndicator(config.window))
        self.register_rule('my_rule', MyRule('my_indicator'))

    def _generate_signal(self, rule_results: dict) -> Signal:
        '''Live: called once per OHLC bar.'''
        return rule_results['my_rule']

    def _generate_signals(self, results: pd.DataFrame) -> pd.Series:
        '''Vectorised: called with full historical DataFrame for backtesting.'''
        return results['my_rule']
```

## Config pattern

```python
@dataclass(frozen=True)
class MyStrategyConfig:
    '''
    Configuration for MyStrategy.

    Attributes:
        window (int): Lookback window size in bars.
    '''
    window: int

    def __post_init__(self):
        if self.window < 2:
            raise ValueError(f'window must be >= 2, got {self.window}')
```

## Factory registration

```python
# scalper/strategy_manager/factory.py
STRATEGIES = {
    ...
    'MyStrategy': (MyStrategy, MyStrategyConfig),
}
```

---

## Existing indicators and rules — check before creating

Before adding a new indicator or rule, confirm an existing one doesn't already do the job. Read
the directories at the time of writing (the list below may drift):

```bash
ls scalper/strategy_manager/indicators
ls scalper/strategy_manager/rules
```

At the time the prompt was written, this included:

- **Indicators:** `SmaIndicator`, `EmaIndicator`, `RsiIndicator`, `AtrIndicator`,
  `AdxIndicator`
- **Rules:** `MaCrossoverRule`, `RsiThresholdRule`, `AdxThresholdRule`, `AtrThresholdRule`

---

## Checklist

- [ ] Config is a frozen dataclass with `__post_init__` validation
- [ ] Strategy implements **both** `_generate_signal` and `_generate_signals`
- [ ] Both methods return identical logic on identical data
- [ ] Indicators with state use `deque(maxlen=window)` for bounded memory
- [ ] Strategy registered in `STRATEGIES` dict in `factory.py`
- [ ] Strategy params added to `scalper/utils/strategy_configs.py` for backtesting and optimisation
- [ ] Exported from `strategies/__init__.py` and `strategy_manager/__init__.py`
- [ ] Unit tests cover: config validation edge cases, indicator output, signal generation
- [ ] Test verifies live and vectorised paths produce identical output on sample data
- [ ] New markers registered in `pytest.ini`
- [ ] `docs/strategy_manager/` mentions the new strategy

For style/architecture rules referenced above (frozen dataclasses, type hints, British English,
test naming, marker hierarchy), see `CLAUDE.md`, `.claude/rules/architecture.md`, and
`.claude/rules/testing.md`.
