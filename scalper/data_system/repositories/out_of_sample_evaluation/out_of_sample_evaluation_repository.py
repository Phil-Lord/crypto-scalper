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
    def get_trial_numbers(self, study_name: str) -> set[int]:
        '''
        Fetches every trial number with at least one evaluation for a study,
        across all time windows.

        :param study_name: Name of the Optuna study.
        :return: Set of distinct trial numbers with stored evaluations.
        '''
        pass

    @abstractmethod
    def remap_trial_numbers(self, study_name: str, mapping: dict[int, int]) -> None:
        '''
        Rewrites trial numbers for a study after compaction renumbers its trials.

        Rows whose trial number is absent from ``mapping`` belong to trials
        dropped by the compaction and are deleted — leaving them would let
        stale evaluations join against unrelated trials that reuse the number.

        :param study_name: Name of the Optuna study.
        :param mapping: Old trial number → new trial number. May be empty, in
            which case every row for the study is deleted.
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
        self, study_name: str, floor: float, drawdown_limit: float
    ) -> list[OosWindowAggregate]:
        '''
        Aggregates evaluation rows for a study by ``(start_timestamp, end_timestamp)``.

        For each window, returns the best OOS balance ratio alongside counts of
        trials that generalised vs overfit. A trial overfits when its OOS
        balance ratio is below ``floor`` OR when ``is_value - oos > drawdown_limit``.

        :param study_name: Name of the Optuna study.
        :param floor: Minimum OOS balance ratio a trial must reach to be
            considered generalising (e.g. ``1.0`` = must end at or above
            starting capital).
        :param drawdown_limit: Maximum allowed gap ``is_value - oos``. Caps how
            much performance is permitted to "drop" between IS and OOS.
        :return: One aggregate per evaluated window, ordered by start timestamp.
            Empty if the study has no OOS evaluations yet.
        '''
        pass
