from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text

from data_system.clients.sqlalchemy_client import SQLAlchemyClient
from data_system.models.oos_window_aggregate_model import OosWindowAggregate
from data_system.models.out_of_sample_evaluation_model import OutOfSampleEvaluation
from data_system.repositories.out_of_sample_evaluation.sqlalchemy_out_of_sample_evaluation_repository import (
    SQLAlchemyOutOfSampleEvaluationRepository,
)


@pytest.mark.data_system
@pytest.mark.repositories
@pytest.mark.sqlalchemy_out_of_sample_evaluation_repository
class TestSQLAlchemyOutOfSampleEvaluationRepository:
    @pytest.fixture
    def mock_session(self, mocker):
        return mocker.MagicMock()

    @pytest.fixture
    def mock_client(self, mocker, mock_session):
        client = mocker.MagicMock(spec=SQLAlchemyClient)

        @contextmanager
        def session_context():
            yield mock_session

        client.session = session_context
        return client

    @pytest.fixture
    def sample_evaluation(self) -> OutOfSampleEvaluation:
        return OutOfSampleEvaluation(
            study_name='test_study',
            trial_number=1,
            start_timestamp=1704067200.0,
            end_timestamp=1704153600.0,
            is_value=1.15,
            oos_balance_ratio=1.0025
        )

    def test_add_with_empty_list_does_nothing(self, mocker):
        # Given
        mock_client = mocker.MagicMock(spec=SQLAlchemyClient)
        repository = SQLAlchemyOutOfSampleEvaluationRepository(mock_client)

        # When
        repository.add([])

        # Then
        mock_client.session.assert_not_called()

    def test_add_inserts_evaluations(self, mock_client, mock_session, sample_evaluation: OutOfSampleEvaluation):
        # Given
        repository = SQLAlchemyOutOfSampleEvaluationRepository(mock_client)

        # When
        repository.add([sample_evaluation])

        # Then
        mock_session.execute.assert_called_once()

    def test_add_passes_correct_records_to_execute(self, mock_client, mock_session, sample_evaluation: OutOfSampleEvaluation):
        # Given
        repository = SQLAlchemyOutOfSampleEvaluationRepository(mock_client)

        # When
        repository.add([sample_evaluation])

        # Then
        call_args = mock_session.execute.call_args
        records = call_args[0][1]
        assert len(records) == 1
        assert records[0]['study_name'] == sample_evaluation.study_name
        assert records[0]['trial_number'] == sample_evaluation.trial_number

    def test_add_handles_multiple_evaluations(self, mock_client, mock_session):
        # Given
        evaluations = [
            OutOfSampleEvaluation(
                study_name='test_study',
                trial_number=i,
                start_timestamp=1704067200.0,
                end_timestamp=1704153600.0,
                is_value=1.15 + i * 0.01,
                oos_balance_ratio=1.0025 + i * 0.001
            )
            for i in range(3)
        ]
        repository = SQLAlchemyOutOfSampleEvaluationRepository(mock_client)

        # When
        repository.add(evaluations)

        # Then
        call_args = mock_session.execute.call_args
        records = call_args[0][1]
        assert len(records) == 3
        assert records[0]['trial_number'] == 0
        assert records[1]['trial_number'] == 1
        assert records[2]['trial_number'] == 2

    def test_get_evaluated_trial_numbers_returns_empty_set_when_no_results(self, mock_client, mock_session):
        # Given
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyOutOfSampleEvaluationRepository(mock_client)

        # When
        result = repository.get_evaluated_trial_numbers(
            study_name='test_study',
            start=1704067200.0,
            end=1704153600.0
        )

        # Then
        assert result == set()

    def test_get_evaluated_trial_numbers_returns_trial_numbers(self, mock_client, mock_session):
        # Given
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(1,), (2,), (5,)]
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyOutOfSampleEvaluationRepository(mock_client)

        # When
        result = repository.get_evaluated_trial_numbers(
            study_name='test_study',
            start=1704067200.0,
            end=1704153600.0
        )

        # Then
        assert result == {1, 2, 5}

    def test_get_evaluated_trial_numbers_passes_correct_params(self, mock_client, mock_session):
        # Given
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyOutOfSampleEvaluationRepository(mock_client)
        study_name = 'my_study'
        start = 1704067200.0
        end = 1704153600.0

        # When
        repository.get_evaluated_trial_numbers(study_name, start, end)

        # Then
        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        assert params['study_name'] == study_name
        assert params['start'] == start
        assert params['end'] == end

    def test_aggregate_windows_returns_empty_when_no_rows(self, mock_client, mock_session):
        # Given
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyOutOfSampleEvaluationRepository(mock_client)

        # When
        result = repository.aggregate_windows('test_study', floor=1.0, drawdown_limit=0.5)

        # Then
        assert result == []

    def test_aggregate_windows_maps_rows_to_domain_objects(self, mock_client, mock_session):
        # Given
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1.0, 2.0, 1.2, 3, 1),
            (3.0, 4.0, 0.4, 0, 2),
        ]
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyOutOfSampleEvaluationRepository(mock_client)

        # When
        result = repository.aggregate_windows('study-x', floor=1.0, drawdown_limit=0.5)

        # Then
        assert result == [
            OosWindowAggregate(start=1.0, end=2.0, best_oos=1.2,
                               generalised_count=3, overfit_count=1),
            OosWindowAggregate(start=3.0, end=4.0, best_oos=0.4,
                               generalised_count=0, overfit_count=2),
        ]

    def test_aggregate_windows_passes_thresholds_and_study_name(self, mock_client, mock_session):
        # Given
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyOutOfSampleEvaluationRepository(mock_client)

        # When
        repository.aggregate_windows('study-x', floor=1.1, drawdown_limit=0.75)

        # Then
        params = mock_session.execute.call_args[0][1]
        assert params['study_name'] == 'study-x'
        assert params['floor'] == 1.1
        assert params['drawdown_limit'] == 0.75


@pytest.mark.data_system
@pytest.mark.repositories
@pytest.mark.sqlalchemy_out_of_sample_evaluation_repository
class TestTrialNumberRemapping:
    '''
    Compaction-support methods exercised against a real SQLite database —
    remapping rewrites primary-key columns, which mock-based tests can't
    meaningfully verify.
    '''

    @pytest.fixture
    def repository(self, tmp_path) -> SQLAlchemyOutOfSampleEvaluationRepository:
        client = SQLAlchemyClient(url=f'sqlite:///{tmp_path}/scalper.db')
        with client.session() as session:
            session.execute(text("""
                CREATE TABLE out_of_sample_evaluation (
                    study_name TEXT NOT NULL,
                    trial_number INTEGER NOT NULL,
                    start_timestamp REAL NOT NULL,
                    end_timestamp REAL NOT NULL,
                    is_value REAL NOT NULL,
                    oos_balance_ratio REAL NOT NULL,
                    PRIMARY KEY (study_name, trial_number, start_timestamp, end_timestamp)
                )
            """))
        return SQLAlchemyOutOfSampleEvaluationRepository(client)

    def _evaluation(
        self, trial_number: int, study_name: str = 'study-a', start: float = 1.0
    ) -> OutOfSampleEvaluation:
        return OutOfSampleEvaluation(
            study_name=study_name,
            trial_number=trial_number,
            start_timestamp=start,
            end_timestamp=start + 1.0,
            is_value=1.15,
            oos_balance_ratio=1.0025,
        )

    def test_get_trial_numbers_returns_empty_set_when_no_rows(self, repository):
        assert repository.get_trial_numbers('study-a') == set()

    def test_get_trial_numbers_returns_distinct_numbers_across_windows(self, repository):
        # Given trial 5 evaluated in two windows, trial 7 in one
        repository.add([
            self._evaluation(5, start=1.0),
            self._evaluation(5, start=10.0),
            self._evaluation(7, start=1.0),
            self._evaluation(9, study_name='study-b'),
        ])

        # When / Then
        assert repository.get_trial_numbers('study-a') == {5, 7}

    def test_remap_rewrites_numbers_and_deletes_unmapped_rows(self, repository):
        # Given trials 5 and 7 are kept by compaction, trial 3 is dropped
        repository.add([
            self._evaluation(3),
            self._evaluation(5),
            self._evaluation(7),
        ])

        # When
        repository.remap_trial_numbers('study-a', {5: 0, 7: 1})

        # Then
        assert repository.get_trial_numbers('study-a') == {0, 1}

    def test_remap_handles_overlapping_old_and_new_ranges(self, repository):
        # Given a swap where each trial's new number is another's old number
        repository.add([self._evaluation(0), self._evaluation(1)])

        # When
        repository.remap_trial_numbers('study-a', {0: 1, 1: 0})

        # Then
        rows = repository.get('study-a', 1.0, 2.0)
        assert {r.trial_number for r in rows} == {0, 1}

    def test_remap_preserves_row_values_under_new_number(self, repository):
        # Given
        original = self._evaluation(5)
        repository.add([original])

        # When
        repository.remap_trial_numbers('study-a', {5: 2})

        # Then
        (row,) = repository.get('study-a', 1.0, 2.0)
        assert row.trial_number == 2
        assert row.is_value == original.is_value
        assert row.oos_balance_ratio == original.oos_balance_ratio

    def test_remap_with_empty_mapping_deletes_all_rows_for_study(self, repository):
        repository.add([self._evaluation(5), self._evaluation(7)])

        repository.remap_trial_numbers('study-a', {})

        assert repository.get_trial_numbers('study-a') == set()

    def test_remap_leaves_other_studies_untouched(self, repository):
        repository.add([
            self._evaluation(5),
            self._evaluation(5, study_name='study-b'),
        ])

        repository.remap_trial_numbers('study-a', {5: 0})

        assert repository.get_trial_numbers('study-b') == {5}

    def test_remap_with_no_rows_is_a_no_op(self, repository):
        repository.remap_trial_numbers('study-a', {5: 0})

        assert repository.get_trial_numbers('study-a') == set()
