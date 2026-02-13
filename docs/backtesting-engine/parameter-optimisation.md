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

# Create engine with base configuration
engine = BacktestingEngine(
    pair='XXBTZGBP',
    strategy_name='PrecisionTrendStrategy',
    repository=repository,
    start=1609459200.0,
    end=1625097600.0,
    interval=1
)

# Define parameter grid
param_grid = {
    'short_ema': [5, 20],
    'long_ema': [15, 50],
    'rsi_buy': [20, 40],
    'rsi_sell': [60, 80]
}

# Run optimisation
engine.optimise_parameters(param_grid, n_trials=100)
```

---

## Window Strategy

**Rolling 3-month windows with 1-month steps:**

- Each window: exactly 3 calendar months
- Step forward: 1 month between windows
- Warmup: From 2nd window onward, start 1 day earlier for indicator preparation
- Incomplete windows: Discarded if < 3 months remain

**Example:**  
Period: `2021-01-10` → `2021-07-10`

| Window | Start (local)       | End (exclusive)     | Warmup |
| ------ | ------------------- | ------------------- | ------ |
| 1      | 2021-01-10 00:00:00 | 2021-04-09 23:59:59 | None   |
| 2      | 2021-02-09 00:00:00 | 2021-05-09 23:59:59 | 1 day  |
| 3      | 2021-03-09 00:00:00 | 2021-06-09 23:59:59 | 1 day  |
| 4      | 2021-04-09 00:00:00 | 2021-07-09 23:59:59 | 1 day  |

---

## Activity Penalty

**Purpose:** Discourage overtrading (too many signals reduce profitability in practice)

**Mechanism:** Logistic penalty curve based on trade count vs ideal rate

- **Ideal:** 0.3 trades/day (roughly 1 trade every 3 days)
- **Penalty:** Scales from 0 (no trades) to 1.0 (ideal or above)
- **Formula:** `min(1.0, (2 / (1 + exp(-0.02 * (count - ideal)))))`

**Effect:**

- Too few trades → Lower penalty multiplier → Reduced score
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

**Why geometric mean?**

- Accounts for compounding effects
- Penalises inconsistency (one bad window hurts overall score)
- More robust than arithmetic mean for return ratios

---

## Optuna Study Storage

Studies persist in PostgreSQL database for:

- Multi-process parallel optimisation
- Resume interrupted runs
- Analyse trials across multiple sessions

**Configuration:**

```python
# utils/__init__.py
OPTUNA_DB_URL = os.getenv('OPTUNA_DB_URL', 'postgresql://...')
```

**Study naming convention:**  
`{StrategyName}_{Pair}_{StartDate}-{EndDate}`

Example: `PrecisionTrendStrategy_XXBTZGBP_20210101-20211231`

---

## See Also

- [BacktestingEngine Overview](index.md) — Core concepts and main class reference
- [Generalisation Evaluation](generalisation-evaluation.md) — Testing optimised parameters on unseen data
- [Architecture Decision Log](../architecture-decision-log.md) — Rationale for optimisation decisions
