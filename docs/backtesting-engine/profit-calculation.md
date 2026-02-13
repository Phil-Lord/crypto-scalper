# Profit Calculation

The BacktestingEngine provides methods to calculate profits from trading positions and determine final account balances after backtesting.

---

## Position Profits

Calculate profit for each completed buy → sell cycle:

```python
from backtesting_engine import BacktestingEngine

# Create and run backtest
engine = BacktestingEngine(
    pair='XXBTZGBP',
    strategy_name='PrecisionTrendStrategy',
    repository=repository,
    start=1609459200.0,
    end=1625097600.0,
    interval=1,
    short_ema=9,
    long_ema=21
)

results = engine.run()

# Calculate position profits
positions = engine.calculate_position_profits(initial_quote_balance=1000)
```

**Returns DataFrame:**

- `entry_time`: Timestamp of buy signal
- `exit_time`: Timestamp of sell signal
- `profit`: Net profit after fees (can be negative)

**Fees:** 0.04% on both buy and sell sides (Kraken taker fees)

---

## Final Balance

Get ending balance after all trades:

```python
final_balance = engine.get_final_quote_balance(initial_quote_balance=1000)
```

**Behavior:**

- If holding position at end: Values at final market price
- If no trades: Returns initial balance
- If multiple positions: Compounds returns

---

## Integration with BacktestingEngine

Both methods require the backtest to have been run via `engine.run()` before being called, as they analyse the signals DataFrame generated during the backtest.

**Typical workflow:**

```python
# 1. Setup engine
engine = BacktestingEngine(...)

# 2. Run backtest
results = engine.run()

# 3. Analyse profitability
final_balance = engine.get_final_quote_balance(initial_quote_balance=1000)
positions = engine.calculate_position_profits(initial_quote_balance=1000)

# 4. Calculate metrics
total_profit = positions['profit'].sum()
win_rate = (positions['profit'] > 0).sum() / len(positions)
```

---

## See Also

- [BacktestingEngine Overview](index.md) — Core concepts and main class reference
- [Parameter Optimisation](parameter-optimisation.md) — Finding optimal strategy parameters
