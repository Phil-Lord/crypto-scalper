# Out-of-Sample Evaluation

After parameter optimisation, it's critical to test how well the optimised parameters perform on unseen data. This helps identify which parameter sets truly generalise vs those that merely overfit the training period.

---

## Workflow

The BacktestingEngine module provides the `evaluate_out_of_sample()` function to evaluate top-performing parameter sets on a new time period:

```python
from backtesting_engine import evaluate_out_of_sample

# Evaluate top 10 parameter sets on a new time period
evaluate_out_of_sample(
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

> **Current limitation:** `evaluate_out_of_sample()` constructs the engine with strategy
> `PrecisionTrendStrategy` and pair `XXBTZGBP` hard-coded. Evaluating other
> studies requires either patching the call site or extending the function to
> accept those values.

---

## Metrics Stored

Results are saved to the `out_of_sample_evaluation` table with the following metrics:

- `final_balance`: Total balance on full evaluation period
- `geo_mean_return`: Geometric mean across same rolling windows used in optimisation
- `trial_number`: Link back to original optimisation trial

These metrics allow direct comparison between training performance (from the Optuna study) and evaluation performance (from out-of-sample testing).

---

## Two-Phase Evaluation Strategy

The backtesting workflow follows a clear two-phase pattern:

1. **Optimisation phase** — Find promising parameter sets on historical data (in-sample)
2. **Out-of-sample phase** — Validate those parameters on a different time period

**Why separate phases?**

- Prevents overfitting to training data
- Reveals which strategies adapt to new market conditions
- Enables walk-forward analysis for robust parameter selection

**Example timeline:**

- Training (in-sample): 2021-01-01 → 2021-12-31 (run optimisation)
- Out-of-sample: 2022-01-01 → 2022-12-31 (test generalisation)
- Live trading: 2023+ (deploy only parameters that generalised well)

---

## Integration with BacktestingEngine

The `evaluate_out_of_sample()` function internally creates a new BacktestingEngine instance for each parameter set being evaluated. It:

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
