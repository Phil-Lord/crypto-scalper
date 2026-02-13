# Generalisation Evaluation

After parameter optimisation, it's critical to test how well the optimised parameters perform on unseen data. This helps identify which parameter sets truly generalise vs those that merely overfit the training period.

---

## Workflow

The BacktestingEngine module provides the `find_params()` function to evaluate top-performing parameter sets on a new time period:

```python
from backtesting_engine import find_params

# Evaluate top 10 parameter sets on a new time period
find_params(
    study_name='PrecisionTrendStrategy_XXBTZGBP_20210101-20211231',
    num_sets=10,
    start=1640995200.0,  # 2022-01-01
    end=1672531200.0     # 2023-01-01
)
```

**Parameters:**

- `study_name`: Name of the completed Optuna study
- `num_sets`: Number of top parameter sets to evaluate (default: 10)
- `start`/`end`: Unix timestamps for the evaluation period (must be different from training period)

---

## Metrics Stored

Results are saved to the `generalisation_evaluation` table with the following metrics:

- `final_balance`: Total balance on full evaluation period
- `geo_mean_return`: Geometric mean across same rolling windows used in optimisation
- `trial_number`: Link back to original optimisation trial

These metrics allow direct comparison between training performance (from the Optuna study) and evaluation performance (from generalisation testing).

---

## Two-Phase Evaluation Strategy

The backtesting workflow follows a clear two-phase pattern:

1. **Optimisation phase** — Find promising parameter sets on historical data
2. **Generalisation phase** — Validate those parameters on a different time period

**Why separate phases?**

- Prevents overfitting to training data
- Reveals which strategies adapt to new market conditions
- Enables walk-forward analysis for robust parameter selection

**Example timeline:**

- Training: 2021-01-01 → 2021-12-31 (run optimisation)
- Evaluation: 2022-01-01 → 2022-12-31 (test generalisation)
- Live trading: 2023+ (deploy only parameters that generalised well)

---

## Integration with BacktestingEngine

The `find_params()` function internally creates a new BacktestingEngine instance for each parameter set being evaluated. It:

1. Retrieves the top N parameter sets from the Optuna study
2. For each set, creates a BacktestingEngine with those parameters
3. Runs the backtest on the evaluation period
4. Calculates both final balance and geometric mean return
5. Stores results for later analysis

This reuses the same backtesting logic from the optimisation phase, ensuring consistency in evaluation methodology.

---

## See Also

- [BacktestingEngine Overview](index.md) — Core concepts and main class reference
- [Parameter Optimisation](parameter-optimisation.md) — Initial optimisation workflow
- [Architecture Decision Log](../architecture-decision-log.md) — Rationale for two-phase evaluation
