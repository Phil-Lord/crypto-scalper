# Backtesting Engine

The Backtesting Engine evaluates trading strategies on historical data with Optuna-based parameter optimisation. It integrates with the [Data System](../data-system/index.md) for trade data and [Strategy Manager](../strategy-manager/index.md) for strategy execution.

---

## Key Features

- **Historical Backtesting** — Test strategies on past trade data from any time period
- **Parameter Optimisation** — Multi-window Optuna optimisation with activity penalties
- **Dual Computation Modes** — Vectorised (fast) and iterative (live-compatible) execution
- **Performance Metrics** — Position profits, final balance, trade counts, and returns
- **Out-of-Sample Evaluation** — Evaluate optimised parameters on unseen time periods

---

## Core Components

### BacktestingEngine

The main class for running backtests. Loads trade data, resamples into OHLC intervals, and executes strategies.

```python
from data_system import SQLAlchemyClient, SQLAlchemyTradeRepository
from backtesting_engine import BacktestingEngine
from strategy_manager import create_strategy

# Setup
client = SQLAlchemyClient()
repository = SQLAlchemyTradeRepository(client)

# Construct the strategy (factory builds the right config dataclass)
strategy = create_strategy('PrecisionTrendStrategy', {
    'short_ema': 9,
    'long_ema': 21,
    # ... remaining PrecisionTrendStrategyConfig fields
})

# Create engine
engine = BacktestingEngine(
    pair='XXBTZGBP',
    strategy=strategy,
    repository=repository,
    start=1609459200.0,  # Unix timestamp
    end=1625097600.0,
    interval=1,          # 1-minute candles
    vectorised=True,
)

# Run backtest
results = engine.run()

# Get performance
final_balance = engine.get_final_quote_balance(initial_quote_balance=1000)
positions = engine.calculate_position_profits()
```

**Parameters:**

- `pair`: Trading pair in Kraken format (`XXBTZGBP`)
- `strategy`: A `Strategy` instance — typically built with
  `create_strategy(name, params)` from `strategy_manager`
- `repository`: `TradeRepository` instance for loading historical data
- `start`/`end`: Unix timestamps for time range (optional, defaults to all data)
- `interval`: Resampling interval in minutes (default: 1)
- `vectorised`: If True, uses fast pandas operations; if False, row-by-row (default: True)

---

## Integration

### With Data System

```python
# Local SQLite for backtesting
from data_system import SQLAlchemyClient, SQLAlchemyTradeRepository

client = SQLAlchemyClient()
repository = SQLAlchemyTradeRepository(client)
```

### With Strategy Manager

Strategies extend `Strategy` and implement **dual computation modes**. The base
class supplies `generate_signal()` and `vectorised_compute()`; subclasses provide
the per-mode reductions:

```python
class MyStrategy(Strategy):
    def _generate_signal(self, rule_results: dict) -> Signal:
        '''Reduce rule results to a single live-mode signal.'''
        ...

    def _generate_signals(self, results: pd.DataFrame) -> pd.Series:
        '''Reduce rule columns to a vectorised signal series.'''
        ...
```

See [Strategy Manager Documentation](../strategy-manager/index.md) for details.

---

## Performance Considerations

### Vectorised vs Iterative

| Mode       | Speed          | Use Case                                          |
| ---------- | -------------- | ------------------------------------------------- |
| Vectorised | 10-100x faster | Parameter optimisation, production backtesting    |
| Iterative  | Slower         | Testing live trading mode, debugging step-by-step |

**Default:** Vectorised mode enabled

**Why dual modes?**

Live trading runs strategies in iterative mode (row-by-row with stateful indicators). The iterative backtest mode allows realistic testing of the same code path that will run in production, ensuring strategies behave identically in both contexts. Debugging is a secondary benefit.

### Memory Management

- **OHLC data**: Loaded once, resampled to interval, kept in memory
- **Window slicing**: Uses pandas `loc[]` for efficient subsetting
- **Results**: Single DataFrame per backtest run

**Typical memory:** ~10MB for 1 year of 1-minute BTC/GBP data

---

## File Structure

```
backtesting_engine/
├── __init__.py                      # Exports BacktestingEngine, evaluate_out_of_sample
├── backtesting_engine.py            # Main BacktestingEngine class
├── objective.py                     # Optuna objective function logic
├── parameter_optimisation.py        # Window creation, study management
├── profit_calculation.py            # Position profits and final balance
└── out_of_sample_evaluation.py      # Post-optimisation evaluation
```

---

## See Also

- [Parameter Optimisation](parameter-optimisation.md) — Optuna-based parameter search with rolling windows
- [Profit Calculation](profit-calculation.md) — Calculating position profits and final balances
- [Out-of-Sample Evaluation](out-of-sample-evaluation.md) — Testing optimised parameters on unseen data
- [Strategy Manager](../strategy-manager/index.md) — Creating backtest-compatible strategies
- [Data System](../data-system/index.md) — Trade data storage and retrieval
- [Architecture Decision Log](../architecture-decision-log.md#backtesting-engine) — Rationale for backtesting design choices
