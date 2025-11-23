Parameter Optimisation Decision Log
============

This section documents key design decisions made during the development
of Crypto-Scalper. It captures the reasoning, trade-offs, and examples
for future reference.

---

Window Creation Logic
---------------------

**Decision:**  
Use rolling 3-month windows with a 1-month step for optimisation.

**Reasoning:**  
- Provides sufficient length to capture multiple market conditions.  
- 1-month step ensures overlapping windows and higher sample density.  
- More robust than using only fixed disjoint periods, which may miss certain behaviours.  

**Details:**
- Incomplete windows at the end of the dataset are discarded.
- Each new window starts 1 day earlier than its nominal boundary to allow indicators to warm up.
- Windows are exclusive at the end.

**Example:**  
- Period: 2021-01-10 → 2022-01-03
- window_months=3, step_months=1, warmup_days=1

Windows generated:
1. Jan 10 00:00:00 → Apr 9 23:59:59 (3 months)
2. Feb 9 00:00:00 → May 9 23:59:59 (3 months + warmup)
3. Mar 9 00:00:00 → Jun 9 23:59:59 (3 months + warmup)
4. Apr 9 00:00:00 → Jul 9 23:59:59 (3 months + warmup)
5. May 9 00:00:00 → Aug 9 23:59:59 (3 months + warmup)
6. Jun 9 00:00:00 → Sep 9 23:59:59 (3 months + warmup)
7. Jul 9 00:00:00 → Oct 9 23:59:59 (3 months + warmup)
8. Aug 9 00:00:00 → Nov 9 23:59:59 (3 months + warmup)
9. Sep 9 00:00:00 → Dec 9 23:59:59 (3 months + warmup)
- Remaining time is discarded as it’s < 3 months:
    - (Oct 9 00:00:00 → Jan 3 00:00:00)

---

Per-Window Averaging
--------------------

**Decision:**  
Compute performance metrics on a *per-window* basis and aggregate using the **geometric mean of return ratios**.  

**Reasoning:**  
- Geometric mean reflects compounding more realistically than arithmetic mean.  
- Keeps results consistent across variable-length test periods.  
- Prevents domination of results by one or two extremely strong windows.  

**Example:**  
If three windows yield return ratios of 1.1, 0.9, and 1.2,  
the geometric mean is ``(1.1 × 0.9 × 1.2)^(1/3) ≈ 1.06``  
(≈ 6% compounded growth per window).  

---

Activity Penalty <WIP>
----------------

**Decision:**  
Apply a penalty based on **trade activity within each window**, without deduplicating overlapping trades.  

**Reasoning:**  
- Prevents optimisation from favouring inactive or "buy-and-hold" strategies.  
- Evaluating activity per window avoids redundancy from overlapping windows.  
- Focus stays on local behaviour, not duplicated counts across overlapping periods.  

**Implementation Notes:**  
- Compute a minimum acceptable trade frequency per window (e.g. ≥1 trade per week).  
- Apply a penalty function if activity falls below threshold.  
- Keep penalty relative rather than absolute, so optimisation balances returns and activity.  

**Example:**  
- Window A: 100 trades → no penalty.  
- Window B: 2 trades → penalty applied.  
- Aggregated metric = geometric mean of penalised window returns.  

---
