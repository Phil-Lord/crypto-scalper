from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

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
            geo_mean_balance_ratio=1.0025
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
                geo_mean_balance_ratio=1.0025 + i * 0.001
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
        result = repository.aggregate_windows('test_study', generalisation_threshold=0.5)

        # Then
        assert result == []

    def test_aggregate_windows_maps_rows_to_domain_objects(self, mock_client, mock_session):
        # Given
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1.0, 2.0, 0.9, 3, 1),
            (3.0, 4.0, 0.4, 0, 2),
        ]
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyOutOfSampleEvaluationRepository(mock_client)

        # When
        result = repository.aggregate_windows('study-x', generalisation_threshold=0.5)

        # Then
        assert result == [
            OosWindowAggregate(start=1.0, end=2.0, best_oos=0.9,
                               generalised_count=3, overfit_count=1),
            OosWindowAggregate(start=3.0, end=4.0, best_oos=0.4,
                               generalised_count=0, overfit_count=2),
        ]

    def test_aggregate_windows_passes_threshold_and_study_name(self, mock_client, mock_session):
        # Given
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyOutOfSampleEvaluationRepository(mock_client)

        # When
        repository.aggregate_windows('study-x', generalisation_threshold=0.75)

        # Then
        params = mock_session.execute.call_args[0][1]
        assert params['study_name'] == 'study-x'
        assert params['threshold'] == 0.75
