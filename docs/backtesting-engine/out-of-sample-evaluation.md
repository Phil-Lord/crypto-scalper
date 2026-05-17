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
    end=1672531200.0,    # 2023-01-01
    n_workers=4,         # process-pool fan-out (default 1 = serial in-process)
)
```

**Parameters:**

- `study_name`: Name of the completed Optuna study
- `num_sets`: Number of top parameter sets to evaluate
- `start`/`end`: Unix timestamps for the evaluation period (must be different from training period)
- `n_workers`: Number of process-pool workers. `1` (default) runs serially in the calling
  process. Values >1 distribute the top parameter sets across `ProcessPoolExecutor` workers,
  each constructing its own `BacktestingEngine` (and loading OHLC data) once.
- `progress_callback`: Optional `() -> None` callback invoked once per parameter set evaluated.
  When `None`, the library installs a default tqdm-backed progress bar to preserve existing
  CLI behaviour.

> **Current limitation:** `evaluate_out_of_sample()` constructs the engine with strategy
> `PrecisionTrendStrategy` and pair `XXBTZGBP` hard-coded. Evaluating other
> studies requires either patching the call site or extending the function to
> accept those values.

---

## Metrics Stored

Results are saved to the `out_of_sample_evaluation` table with the following metrics:

- `trial_number`: Link back to the original optimisation trial
- `geo_mean_balance_ratio`: Geometric mean of per-window balance ratios
  (`final_balance / initial_balance`) across the same rolling windows used during optimisation.
  `1.0` is break-even, `1.1` is +10%, `0.5` is half capital lost.

The geometric mean balance ratio uses the identical window construction (rolling 3-month /
1-month step) as in-sample optimisation, so OOS scores are directly comparable to study trial
values.

> **No whole-period balance column.** Earlier versions also stored a `final_balance` from a
> redundant full-period run. It was dropped — see the
> [Architecture Decision Log](../architecture-decision-log.md#backtesting-engine) for the
> rationale.

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

`evaluate_out_of_sample()` constructs one `BacktestingEngine` (loading OHLC once) and reuses it
across all evaluated parameter sets. It:

1. Retrieves the top N parameter sets from the Optuna study
2. Builds rolling 3-month windows over the evaluation period
3. For each parameter set, evaluates it across every window via the shared
   `evaluate_param_set_over_windows()` helper — which resets the strategy, slices the OHLC
   window, runs the backtest, and captures the final quote balance
4. Computes the geometric mean return ratio across windows
5. Stores results for later analysis

The lower-level `run_strategy_on_window()` helper (which `evaluate_param_set_over_windows()`
calls internally) is also used directly by the in-sample objective, which needs to inspect
`engine.results` between windows for the activity penalty and so cannot use the wrapper
end-to-end. Sharing the per-window run mechanics in one place prevents IS/OOS drift.

When `n_workers > 1`, each `ProcessPoolExecutor` worker builds its own `BacktestingEngine`
once and evaluates its assigned chunk of parameter sets — amortising OHLC load across the
chunk.

---

## See Also

- [BacktestingEngine Overview](index.md) — Core concepts and main class reference
- [Parameter Optimisation](parameter-optimisation.md) — Initial optimisation workflow
- [Architecture Decision Log](../architecture-decision-log.md) — Rationale for two-phase evaluation
