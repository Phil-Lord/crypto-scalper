# Add Strategy

Add a new trading strategy to `scalper/strategy_manager/`.

## Instructions

1. **Clarify requirements** — Confirm strategy name, what indicators/rules it uses, and its
   parameters
2. **Create the config** — Frozen dataclass with validation in `__post_init__`
3. **Create indicators** — Any new indicators needed (reuse existing where possible)
4. **Create rules** — Any new rules needed (reuse existing where possible)
5. **Create the strategy** — Subclass `Strategy`, register indicators and rules in `__init__`
6. **Register in factory** — Add to `STRATEGIES` dict in `factory.py`
7. **Update exports** — Add to `strategies/__init__.py` and `strategy_manager/__init__.py`
8. **Write tests** — Unit tests for config validation, indicator logic, and signal generation
9. **Register markers** — Add class-level marker to `pytest.ini`

---

## File Locations

```
scalper/strategy_manager/
├── strategies/
│   ├── {name}_strategy.py           # Strategy class
│   ├── {name}_strategy_config.py    # Config dataclass
│   └── __init__.py                  # Add exports here
├── indicators/
│   └── {name}_indicator.py          # New indicators (if needed)
├── rules/
│   └── {name}_rule.py               # New rules (if needed)
└── factory.py                       # Register strategy here
```

```
scalper/tests/unit/strategy_manager/
├── strategies/
│   └── test_{name}_strategy.py
├── indicators/
│   └── test_{name}_indicator.py     # If new indicators added
└── rules/
    └── test_{name}_rule.py          # If new rules added
```

---

## Strategy Pattern

Every strategy must implement both `_generate_signal` (live) and `_generate_signals`
(vectorised/backtesting):

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

## Config Pattern

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

## Factory Registration

```python
# factory.py — add to STRATEGIES dict
STRATEGIES = {
    ...
    'MyStrategy': (MyStrategy, MyStrategyConfig),
}
```

---

## Checklist

- [ ] Config is a frozen dataclass with `__post_init__` validation
- [ ] Strategy implements **both** `_generate_signal` and `_generate_signals`
- [ ] Both methods return identical logic (same signals for same data)
- [ ] Indicators use `deque(maxlen=window)` for bounded state
- [ ] Strategy registered in `STRATEGIES` dict in `factory.py`
- [ ] Exported from `strategies/__init__.py` and `strategy_manager/__init__.py`
- [ ] Unit tests cover: config validation edge cases, indicator output, signal generation
- [ ] Tests verify `_generate_signal` and vectorised output agree on sample data
- [ ] Markers registered in `pytest.ini`
- [ ] `strategy_manager` docs updated with new strategy entry

---

## Existing Indicators & Rules

Check these before creating new ones:

**Indicators:** `SmaIndicator`, `EmaIndicator`, `RsiIndicator`, `AtrIndicator`, `AdxIndicator`

**Rules:** `MaCrossoverRule` (and others in `strategy_manager/rules/`)
