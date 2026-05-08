from abc import ABC, abstractmethod

from data_system.models import OosWindowAggregate, OutOfSampleEvaluation


class OutOfSampleEvaluationRepository(ABC):
    @abstractmethod
    def add(self, evaluations: list[OutOfSampleEvaluation]) -> None:
        '''
        Inserts or replaces a list of out-of-sample evaluation results.

        :param evaluations: List of OutOfSampleEvaluation domain objects to persist.
        '''
        pass

    @abstractmethod
    def get_evaluated_trial_numbers(self, study_name: str, start: float, end: float) -> set[int]:
        '''
        Fetches trial numbers that have already been evaluated for a study and time range.

        :param study_name: Name of the Optuna study.
        :param start: Start timestamp (Unix seconds).
        :param end: End timestamp (Unix seconds).
        :return: Set of trial numbers already evaluated.
        '''
        pass

    @abstractmethod
    def get(self, study_name: str, start: float, end: float) -> list[OutOfSampleEvaluation]:
        '''
        Fetches all stored evaluation rows for a study and time range.

        :param study_name: Name of the Optuna study.
        :param start: Start timestamp (Unix seconds).
        :param end: End timestamp (Unix seconds).
        :return: List of OutOfSampleEvaluation rows, ordered by trial number.
        '''
        pass

    @abstractmethod
    def aggregate_windows(
        self, study_name: str, generalisation_threshold: float
    ) -> list[OosWindowAggregate]:
        '''
        Aggregates evaluation rows for a study by ``(start_timestamp, end_timestamp)``.

        For each window, returns the best geo-mean return alongside counts of
        trials whose geo-mean return is at or above the supplied threshold
        (``generalised_count``) and below it (``overfit_count``).

        :param study_name: Name of the Optuna study.
        :param generalisation_threshold: Geo-mean return at or above which a
            trial is considered to have generalised.
        :return: One aggregate per evaluated window, ordered by start timestamp.
            Empty if the study has no OOS evaluations yet.
        '''
        pass
