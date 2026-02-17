# Reference

Complete reference for built-in components, testing, performance, and module integration.

---

## Built-in Components

### Indicators

| Indicator              | Description                | Returns          |
| ---------------------- | -------------------------- | ---------------- |
| `SmaIndicator(window)` | Simple Moving Average      | Price average    |
| `EmaIndicator(window)` | Exponential Moving Average | Weighted average |
| `RsiIndicator(window)` | Relative Strength Index    | 0-100 momentum   |
| `AtrIndicator(window)` | Average True Range         | Volatility ratio |
| `AdxIndicator(window)` | Average Directional Index  | Trend strength   |

### Rules

| Rule                                          | Description              | Signals                                       |
| --------------------------------------------- | ------------------------ | --------------------------------------------- |
| `MaCrossoverRule(short, long)`                | Moving average crossover | BUY on cross above, SELL on cross below       |
| `RsiThresholdRule(rsi, oversold, overbought)` | RSI threshold crosses    | BUY on exit oversold, SELL on exit overbought |
| `AtrThresholdRule(atr, threshold)`            | Volatility filter        | BUY when ATR ≥ threshold                      |
| `AdxThresholdRule(adx, threshold)`            | Trend strength filter    | BUY when ADX ≥ threshold                      |

### Strategies

| Strategy                 | Description                      | Parameters                    |
| ------------------------ | -------------------------------- | ----------------------------- |
| `SmaStrategy`            | SMA crossover                    | `short_window`, `long_window` |
| `PrecisionTrendStrategy` | Multi-indicator weighted scoring | EMA, RSI, ADX, ATR + weights  |

---

## Testing Guidelines

### Test Both Modes

Every indicator and rule should verify that live and vectorised modes produce identical results:

```python
def test_indicator_modes_match():
    # Given
    indicator = MyIndicator(window=10)
    ohlc_df = pd.DataFrame({'price': [100, 102, 104, ...]})

    # When - live mode
    live_results = [indicator.update(row) for _, row in ohlc_df.iterrows()]

    # When - vectorised mode
    vectorised_results = MyIndicator(window=10).compute_vectorised(ohlc_df)

    # Then - results should match
    for i in range(window, len(ohlc_df)):
        assert abs(live_results[i] - vectorised_results.iloc[i]) < 1e-6
```

### Test Edge Cases

- **Warmup period** — Returns `None` until enough data
- **NaN handling** — Gracefully handles missing values
- **Constant prices** — Correct behaviour on flat markets
- **Extreme values** — Division by zero, overflow protection

---

## Performance Considerations

### Backtesting Performance

- **Vectorised mode is 10-100x faster** than calling `update()` in a loop
- Use `.rolling()`, `.ewm()`, and numpy operations
- Avoid Python loops over DataFrame rows

### Live Trading Performance

- **Bounded state** prevents memory leaks in 24/7 operation
- Use `deque(maxlen=N)` for rolling windows
- Avoid storing full price history

### Memory Usage

| Component                  | Memory Footprint               |
| -------------------------- | ------------------------------ |
| `SmaIndicator(50)`         | ~400 bytes (50 floats)         |
| `RsiIndicator(14)`         | ~200 bytes (15 floats + state) |
| Strategy with 4 indicators | ~2 KB                          |

Safe for running hundreds of strategy instances concurrently.

---

## Integration with Other Modules

### Backtesting Engine

```python
from strategy_manager import StrategyManager

manager = StrategyManager()
strategy = manager.get_strategy('SmaStrategy', short_window=10, long_window=50)

# Vectorised backtesting
results = strategy.vectorised_compute(ohlc_data)
```

### Trade Executor

```python
from strategy_manager import StrategyManager

manager = StrategyManager()
strategy = manager.get_strategy('PrecisionTrendStrategy', ...)

# Live trading loop
for ohlc in tick_stream:
    signal_data = strategy.generate_signal(ohlc)
    if signal_data['signal'] != Signal.HOLD:
        execute_trade(signal_data)
```

### Data System

Strategies use `Signal` enum from `data_system` for consistency across persistence:

```python
from data_system import Signal, BotTick

tick = BotTick(
    ...,
    signal=signal_data['signal'],  # Signal enum
    ...
)
```

---

## Future Enhancements

**Considered but not yet implemented:**

1. **State Reset Methods** — Enable strategy reuse across backtest runs
2. **Indicator Factories** — Reduce boilerplate when registering many indicators
3. **Shared Calculation Logic** — Extract common code between dual implementations (where overlap exists)

See Architecture Decision Log for rationale on current design choices.
