from dataclasses import dataclass


@dataclass(frozen=True)
class OutOfSampleEvaluation:
    '''
    Dataclass representing an out-of-sample evaluation result for a parameter set.

    This model stores the results of evaluating an Optuna trial's parameters
    across multiple time windows on data the optimisation never saw, to assess
    how well the parameters generalise (robustness to overfitting).

    Attributes:
        study_name (str): Name of the Optuna study being evaluated.
        trial_number (int): Trial number within the study.
        start_timestamp (float): Start of the evaluation period (Unix seconds).
        end_timestamp (float): End of the evaluation period (Unix seconds).
        geo_mean_return (float): Geometric mean of returns across time windows.

    Database Mapping:
        - study_name: TEXT
        - trial_number: INTEGER
        - start_timestamp: REAL
        - end_timestamp: REAL
        - geo_mean_return: REAL NOT NULL

    Note:
        Primary key is composite (study_name, trial_number, start_timestamp, end_timestamp)
        since the same trial can be evaluated on different time periods.
    '''
    study_name: str
    trial_number: int
    start_timestamp: float
    end_timestamp: float
    geo_mean_return: float
