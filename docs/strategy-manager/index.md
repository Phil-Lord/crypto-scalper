# Strategy Manager

The Strategy Manager module provides a composable framework for building trading strategies with dual computation modes: **live trading** (single signal generation) and **backtesting** (vectorised batch computation).

---

## Overview

The module follows a three-layer architecture:

```
Strategy
   ├── Indicators (technical calculations)
   ├── Rules (signal generation logic)
   └── Signal Combination (weighted scoring, voting, etc.)
```

**Key Features:**

- **Composability** — Mix and match indicators and rules
- **Dual Computation Modes** — Same logic for live and backtesting
- **Type Safety** — Strong typing with `Signal` enum
- **State Management** — Bounded memory usage for 24/7 operation
- **Extensibility** — Easy to add new indicators, rules, and strategies

---

## Architecture

### Three-Layer Pattern

**1. Indicators** — Technical calculations (SMA, RSI, ADX, etc.)

```python
class Indicator(ABC):
    @abstractmethod
    def update(self, ohlc: pd.Series) -> float | None:
        '''Update indicator with new OHLC for live trading.'''

    @abstractmethod
    def compute_vectorised(self, ohlc: pd.DataFrame) -> pd.Series:
        '''Compute indicator for entire series during backtesting.'''

    @abstractmethod
    def reset(self) -> None:
        '''Reset internal state to initial values.'''
```

**2. Rules** — Signal generation logic based on indicator values

```python
class Rule(ABC):
    @abstractmethod
    def check(self, current_state: dict[str, Any]) -> Signal:
        '''Check rule against current state during live trading.'''

    @abstractmethod
    def compute_vectorised(self, results: pd.DataFrame) -> pd.Series:
        '''Compute rule signals across results for backtesting.'''
```

**3. Strategies** — Combine indicators and rules to generate final signals

```python
class Strategy(ABC):
    @property
    @abstractmethod
    def warmup_candles(self) -> int:
        '''Candles required for indicator convergence — read by TradeExecutor.warm_up().'''

    def register_indicator(self, name: str, indicator: Indicator)
    def register_rule(self, name: str, rule: Rule)
    def generate_signal(self, ohlc: pd.Series) -> dict
    def vectorised_compute(self, ohlc: pd.DataFrame) -> pd.DataFrame
    def reset(self) -> None
```

---

## Dual Computation Modes

The Strategy Manager implements each algorithm **twice** to optimise for different use cases:

### Live Trading Mode

**Purpose:** Real-time signal generation for live trading execution

**Characteristics:**

- Stateful (maintains indicator state between updates)
- Single OHLC input → Single signal output
- Optimised for latency

**Example:**

```python
from strategy_manager import SmaStrategy, SmaStrategyConfig

strategy = SmaStrategy(SmaStrategyConfig(short_window=10, long_window=50))

# Process new tick
signal_data = strategy.generate_signal(ohlc_series)
# {'price': 50000.0, 'short_sma': 49800.0, 'long_sma': 50200.0,
#  'crossover': Signal.HOLD, 'signal': Signal.HOLD}
```

### Backtesting Mode

**Purpose:** Bulk processing for parameter optimisation and historical analysis

**Characteristics:**

- Stateless (computes over entire DataFrame)
- Batch OHLC input → Batch signal output
- Optimised for throughput (vectorised pandas operations)

**Example:**

```python
strategy = SmaStrategy(SmaStrategyConfig(short_window=10, long_window=50))

# Process historical data
results = strategy.vectorised_compute(ohlc_dataframe)
# DataFrame with columns: price, short_sma, long_sma, crossover, signal
```

**Why Dual Implementation?**

- **Performance:** Vectorised operations are 10-100x faster for batch processing
- **Memory:** Live mode uses bounded state (deques); vectorised mode processes in chunks
- **Simplicity:** Each mode optimised for its use case without compromises

**Trade-off:** Code duplication requires maintaining two implementations. Mitigated by comprehensive tests ensuring parity.

---

## Signal Type

Signals use the `Signal` enum from `data_system`:

```python
from data_system import Signal

class Signal(str, Enum):
    BUY = 'buy'
    HOLD = 'hold'
    SELL = 'sell'
```

**Benefits:**

- Type safety (IDE autocomplete, type checking)
- String compatibility (`Signal.BUY == 'buy'`)
- Centralised definition across modules

---

## Next Steps

- **[Creating Components](creating-components.md)** — Build custom strategies, indicators, and rules
- **[Reference](reference.md)** — Built-in components, testing, performance, and integration
