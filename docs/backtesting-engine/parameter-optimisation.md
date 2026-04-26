# Parameter Optimisation

The BacktestingEngine uses Optuna-based parameter optimisation to find effective strategy configurations across multiple time windows.

---

## Workflow

1. **Define parameter space** — Specify ranges for each strategy parameter
2. **Rolling window evaluation** — Test parameter combinations across multiple 3-month windows
3. **Activity-penalised scoring** — Geometric mean of returns, adjusted for trade frequency
4. **Concurrent optimisation** — Optuna runs trials in parallel with smart sampling

```python
from backtesting_engine import BacktestingEngine
from strategy_manager import create_strategy

# Build a seed strategy — Optuna replaces it per trial via create_strategy()
strategy = create_strategy('PrecisionTrendStrategy', seed_params)

engine = BacktestingEngine(
    pair='XXBTZGBP',
    strategy=strategy,
    repository=repository,
    start=1609459200.0,
    end=1625097600.0,
    interval=1
)

# Define parameter grid (each entry is a [low, high] range)
param_grid = {
    'short_ema': [5, 20],
    'long_ema': [15, 50],
    'rsi_oversold': [20, 40],
    'rsi_overbought': [60, 80]
}

# Run optimisation
engine.optimise_parameters(param_grid, n_trials=100)
```

---

## Parameter Validation

**Config-based validation** — Parameter constraints are enforced in strategy config dataclasses using `__post_init__` validation.

**Example:**

```python
@dataclass(frozen=True)
class PrecisionTrendStrategyConfig:
    short_ema: int
    long_ema: int
    rsi_oversold: float
    rsi_overbought: float

    def __post_init__(self):
        if self.short_ema >= self.long_ema:
            raise ValueError(
                f'short_ema ({self.short_ema}) must be < long_ema ({self.long_ema})'
            )
        if self.rsi_oversold >= self.rsi_overbought:
            raise ValueError(
                f'rsi_oversold ({self.rsi_oversold}) must be < rsi_overbought ({self.rsi_overbought})'
            )
```

**During optimisation:**

- Optuna suggests parameter combinations within the defined ranges
- Config instantiation validates constraints
- Invalid combinations raise `ValueError`, which is caught and converted to `optuna.TrialPruned`
- Pruned trials don't affect study statistics and are efficiently skipped

**Benefits:**

- **Single source of truth** — Constraints defined once in config
- **Runtime safety** — Same validation applies in backtesting and live trading
- **Type safety** — Config dataclasses provide IDE support and type checking
- **No duplication** — Eliminates need for separate constraint functions

---

## Window Strategy

**Rolling 3-month windows with 1-month steps:**

- Each window: exactly 3 calendar months
- Step forward: 1 month between windows
- Warmup: From 2nd window onward, start 1 day earlier for indicator preparation
- Incomplete windows: Discarded if < 3 months remain

**Reasoning:**

- 3-month length provides sufficient data to capture multiple market conditions
- 1-month step ensures overlapping windows and higher sample density
- More robust than fixed disjoint periods, which may miss certain behaviours

**Example:**  
Period: `2021-01-10` → `2022-01-03`

| Window | Start (local)       | End (exclusive)     | Warmup |
| ------ | ------------------- | ------------------- | ------ |
| 1      | 2021-01-10 00:00:00 | 2021-04-09 23:59:59 | None   |
| 2      | 2021-02-09 00:00:00 | 2021-05-09 23:59:59 | 1 day  |
| 3      | 2021-03-09 00:00:00 | 2021-06-09 23:59:59 | 1 day  |
| 4      | 2021-04-09 00:00:00 | 2021-07-09 23:59:59 | 1 day  |
| 5      | 2021-05-09 00:00:00 | 2021-08-09 23:59:59 | 1 day  |
| 6      | 2021-06-09 00:00:00 | 2021-09-09 23:59:59 | 1 day  |
| 7      | 2021-07-09 00:00:00 | 2021-10-09 23:59:59 | 1 day  |
| 8      | 2021-08-09 00:00:00 | 2021-11-09 23:59:59 | 1 day  |
| 9      | 2021-09-09 00:00:00 | 2021-12-09 23:59:59 | 1 day  |

Remaining time (2021-10-09 → 2022-01-03) is discarded as it's < 3 months.

---

## Activity Penalty

**Purpose:** Incentivise active trading to prevent buy-and-hold strategies while discouraging excessive overtrading

Early optimisation runs favoured inactive "buy-and-hold" strategies that simply held positions for the entire backtest period rather than actively scalping to catch highs and lows. The activity penalty ensures strategies demonstrate genuine trading activity.

**Mechanism:** Logistic penalty curve based on trade count vs ideal rate

- **Ideal:** 0.3 trades/day (roughly 1 trade every 3 days)
- **Penalty:** Scales from 0 (no trades) to 1.0 (ideal or above)
- **Formula:** `min(1.0, (2 / (1 + exp(-0.02 * (count - ideal)))))`

**Effect:**

- Too few trades → Lower penalty multiplier → Reduced score (prevents buy-and-hold)
- Ideal trade count → Penalty = 1.0 → No reduction
- Excessive trades → Capped at 1.0 (no additional penalty beyond ideal)

---

## Scoring Function

**Objective:** Maximise geometric mean of adjusted returns across windows

```python
# For each window:
window_return = final_balance / initial_balance  # e.g., 1.05 = +5%
adjusted_return = window_return * activity_penalty

# Aggregate across all windows:
score = (product of all adjusted_returns) ** (1 / num_windows)
```

**Example:**

If three windows yield return ratios of 1.1, 0.9, and 1.2, the geometric mean is:

`(1.1 × 0.9 × 1.2)^(1/3) ≈ 1.06` (≈ 6% compounded growth per window)

**Why geometric mean?**

- Reflects compounding more realistically than arithmetic mean
- Penalises inconsistency (one bad window hurts overall score)
- Prevents domination by one or two extremely strong windows
- Keeps results consistent across variable-length test periods

---

## Optuna Study Storage

Studies persist in PostgreSQL database for:

- Multi-process parallel optimisation
- Resume interrupted runs
- Analyse trials across multiple sessions

**Configuration:**

`OptunaConfig.DB_URL` (in `utils/`) reads `OPTUNA_DB_URL` lazily via metaclass
properties so studies pick up the value at access time, not import time.

**Study naming convention:**  
`{StrategyName}_{Pair}_{StartDate}-{EndDate}`

Example: `PrecisionTrendStrategy_XXBTZGBP_20210101-20211231`

---

## See Also

- [BacktestingEngine Overview](index.md) — Core concepts and main class reference
- [Generalisation Evaluation](generalisation-evaluation.md) — Testing optimised parameters on unseen data
- [Architecture Decision Log](../architecture-decision-log.md) — Rationale for optimisation decisions
