# Creating Components

This guide covers how to build custom strategies, indicators, and rules for the Strategy Manager.

---

## Creating Custom Strategies

### 1. Simple Strategy (Single Rule)

```python
class SmaStrategy(Strategy):
    def __init__(self, short_window: int, long_window: int):
        super().__init__()
        self.register_indicator('short_sma', SmaIndicator(short_window))
        self.register_indicator('long_sma', SmaIndicator(long_window))
        self.register_rule('crossover', MaCrossoverRule('short_sma', 'long_sma'))

    def _generate_signal(self, rule_results: dict) -> Signal:
        return rule_results['crossover']

    def _generate_signals(self, results: pd.DataFrame) -> pd.Series:
        return results['crossover']
```

### 2. Complex Strategy (Weighted Scoring)

```python
class PrecisionTrendStrategy(Strategy):
    def __init__(self, ..., weight_crossover, weight_rsi, ...):
        super().__init__()
        # Register indicators
        self.register_indicator('short_ema', EmaIndicator(short_ema))
        self.register_indicator('rsi', RsiIndicator(rsi_window))

        # Register rules
        self.register_rule('crossover', MaCrossoverRule('short_ema', 'long_ema'))
        self.register_rule('rsi_threshold', RsiThresholdRule('rsi', oversold, overbought))

        # Normalise weights
        total = weight_crossover + weight_rsi + ...
        self.weight_crossover = weight_crossover / total
        self.weight_rsi = weight_rsi / total

    def _generate_signal(self, rule_results: dict) -> Signal:
        # Weighted scoring
        signal_map = {Signal.BUY: 1, Signal.HOLD: 0, Signal.SELL: -1}
        score = (
            self.weight_crossover * signal_map[rule_results['crossover']] +
            self.weight_rsi * signal_map[rule_results['rsi_threshold']]
        )

        if score > self.buy_threshold:
            return Signal.BUY
        elif score < self.sell_threshold:
            return Signal.SELL
        return Signal.HOLD
```

---

## Creating Custom Indicators

### Pattern

```python
class MyIndicator(Indicator):
    def __init__(self, window: int):
        self.window = window
        # Initialise bounded state
        self.prices = deque(maxlen=window)

    def update(self, ohlc: pd.Series) -> float | None:
        '''Live mode: stateful, incremental calculation.'''
        self.prices.append(ohlc['price'])
        if len(self.prices) < self.window:
            return None
        # Calculate indicator value
        return calculate_from_state(self.prices)

    def compute_vectorised(self, ohlc: pd.DataFrame) -> pd.Series:
        '''Backtest mode: stateless, vectorised calculation.'''
        return ohlc['price'].rolling(self.window).apply(calculate)

    def reset(self) -> None:
        '''Reset state to initial values.'''
        self.prices = deque(maxlen=self.window)
```

### State Management Guidelines

**Implement `reset()` to mirror `__init__` state:**

```python
# ✅ Good - reset mirrors __init__
def __init__(self, window: int):
    self.window = window
    self.ema = None

def reset(self) -> None:
    self.ema = None

# ❌ Bad - reset misses state
def reset(self) -> None:
    pass  # Forgot to clear self.ema
```

**Use bounded collections:**

```python
# ✅ Good - bounded memory
self.prices = deque(maxlen=window)

# ❌ Bad - unbounded growth
self.prices = []
```

**Return `None` during warmup:**

```python
if len(self.prices) < self.window:
    return None  # Not enough data yet
```

**Store minimal state:**

```python
# ✅ Good - store running average
self.ema = calculate_ema(price, self.ema)

# ❌ Bad - store entire history
self.prices.append(price)
```

---

## Creating Custom Rules

### Pattern

```python
class MyRule(Rule):
    def __init__(self, indicator_name: str, threshold: float):
        self.indicator_name = indicator_name
        self.threshold = threshold

    def check(self, current_state: dict) -> Signal:
        '''Live mode: check current state.'''
        value = current_state[self.indicator_name]
        if value is None:
            return Signal.HOLD
        return Signal.BUY if value > self.threshold else Signal.HOLD

    def compute_vectorised(self, results: pd.DataFrame) -> pd.Series:
        '''Backtest mode: vectorised logic.'''
        return np.where(
            results[self.indicator_name] > self.threshold,
            Signal.BUY,
            Signal.HOLD
        )
```

### Crossover Detection

For crossover rules that need previous values:

```python
def check(self, current_state: dict) -> Signal:
    current = current_state['short_ma']
    previous = current_state.get('prev_short_ma', None)

    if None in (current, previous):
        return Signal.HOLD

    if current > threshold and previous <= threshold:
        return Signal.BUY
```

Note: `prev_*` values are automatically stored by `Strategy.generate_signal()`.
