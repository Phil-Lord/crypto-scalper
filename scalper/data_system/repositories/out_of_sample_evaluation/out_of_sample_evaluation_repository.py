from abc import ABC, abstractmethod

from data_system.models import OutOfSampleEvaluation


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
