from dataclasses import dataclass


@dataclass(frozen=True)
class GeneralisationEvaluation:
    '''
    Dataclass representing a generalisation evaluation result for a parameter set.

    This model stores the results of evaluating an Optuna trial's parameters
    across multiple time windows to assess generalisation (robustness to overfitting).

    Attributes:
        study_name (str): Name of the Optuna study being evaluated.
        trial_number (int): Trial number within the study.
        start_timestamp (float): Start of the evaluation period (Unix seconds).
        end_timestamp (float): End of the evaluation period (Unix seconds).
        final_balance (float): Final balance when running on the full period.
        geo_mean_return (float): Geometric mean of returns across time windows.

    Database Mapping:
        - study_name: TEXT
        - trial_number: INTEGER
        - start_timestamp: REAL
        - end_timestamp: REAL
        - final_balance: REAL NOT NULL
        - geo_mean_return: REAL NOT NULL

    Note:
        Primary key is composite (study_name, trial_number, start_timestamp, end_timestamp)
        since the same trial can be evaluated on different time periods.
    '''
    study_name: str
    trial_number: int
    start_timestamp: float
    end_timestamp: float
    final_balance: float
    geo_mean_return: float
