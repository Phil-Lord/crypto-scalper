from dataclasses import dataclass


@dataclass(frozen=True)
class OosWindowAggregate:
    '''
    Aggregate of out-of-sample evaluations for a single ``(start, end)`` window.

    Attributes:
        start (float): Window start (Unix seconds).
        end (float): Window end (Unix seconds).
        best_oos (float): Highest geo-mean OOS return across evaluated trials.
        generalised_count (int): Trials with geo-mean OOS return at or above
            the caller-supplied generalisation threshold.
        overfit_count (int): Trials with geo-mean OOS return below the
            caller-supplied generalisation threshold.

    Note:
        Threshold-based counts are computed by the repository using a value
        passed in by the caller — this model has no opinion on what counts as
        generalisation, so it stays free of any ``backtesting_engine``
        dependency.
    '''
    start: float
    end: float
    best_oos: float
    generalised_count: int
    overfit_count: int
