from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from data_system.clients.sqlalchemy_client import SQLAlchemyClient
from data_system.models.job_model import Job, JobStatus, JobType
from data_system.repositories.job.sqlalchemy_job_repository import SQLAlchemyJobRepository


@pytest.mark.data_system
@pytest.mark.repositories
@pytest.mark.sqlalchemy_job_repository
class TestSQLAlchemyJobRepository:
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
    def sample_job(self) -> Job:
        return Job(
            job_type=JobType.GET_TRADES,
            id=UUID('12345678-1234-5678-1234-567812345678'),
            status=JobStatus.PENDING,
            message='',
            created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        )

    def test_add_calls_session_execute_once(self, mock_client, mock_session, sample_job: Job):
        # Given
        repository = SQLAlchemyJobRepository(mock_client)

        # When
        repository.add(sample_job)

        # Then
        mock_session.execute.assert_called_once()

    def test_add_passes_correct_record(self, mock_client, mock_session, sample_job: Job):
        # Given
        repository = SQLAlchemyJobRepository(mock_client)

        # When
        repository.add(sample_job)

        # Then
        call_args = mock_session.execute.call_args
        record = call_args[0][1]
        assert record['id'] == str(sample_job.id)
        assert record['job_type'] == sample_job.job_type.value
        assert record['status'] == sample_job.status.value
        assert record['message'] == sample_job.message
        assert record['created_at'] == sample_job.created_at.timestamp()
        assert record['updated_at'] == sample_job.updated_at.timestamp()

    def test_update_calls_session_execute_once(self, mock_client, mock_session, sample_job: Job):
        # Given
        repository = SQLAlchemyJobRepository(mock_client)
        sample_job.update(status=JobStatus.RUNNING, message='progress')

        # When
        repository.update(sample_job)

        # Then
        mock_session.execute.assert_called_once()

    def test_update_passes_correct_record(self, mock_client, mock_session, sample_job: Job):
        # Given
        repository = SQLAlchemyJobRepository(mock_client)
        sample_job.update(status=JobStatus.DONE, message='finished')

        # When
        repository.update(sample_job)

        # Then
        call_args = mock_session.execute.call_args
        record = call_args[0][1]
        assert record['id'] == str(sample_job.id)
        assert record['status'] == 'done'
        assert record['message'] == 'finished'
        assert record['updated_at'] == sample_job.updated_at.timestamp()

    def test_get_by_id_returns_none_when_not_found(self, mock_client, mock_session):
        # Given
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyJobRepository(mock_client)

        # When
        result = repository.get_by_id('non-existent-id')

        # Then
        assert result is None

    def test_get_by_id_returns_job_when_found(self, mock_client, mock_session, sample_job: Job):
        # Given
        row = (
            str(sample_job.id),
            sample_job.job_type.value,
            sample_job.status.value,
            sample_job.message,
            sample_job.created_at.timestamp(),
            sample_job.updated_at.timestamp(),
        )
        mock_result = MagicMock()
        mock_result.fetchone.return_value = row
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyJobRepository(mock_client)

        # When
        result = repository.get_by_id(str(sample_job.id))

        # Then
        assert result is not None
        assert result.id == sample_job.id
        assert result.job_type == sample_job.job_type
        assert result.status == sample_job.status
        assert result.message == sample_job.message
        assert result.created_at == sample_job.created_at
        assert result.updated_at == sample_job.updated_at

    def test_get_by_id_maps_null_message_to_empty_string(self, mock_client, mock_session, sample_job: Job):
        # Given
        row = (
            str(sample_job.id),
            sample_job.job_type.value,
            sample_job.status.value,
            None,
            sample_job.created_at.timestamp(),
            sample_job.updated_at.timestamp(),
        )
        mock_result = MagicMock()
        mock_result.fetchone.return_value = row
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyJobRepository(mock_client)

        # When
        result = repository.get_by_id(str(sample_job.id))

        # Then
        assert result.message == ''

    def test_get_by_id_passes_id_as_string(self, mock_client, mock_session):
        # Given
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyJobRepository(mock_client)
        job_id = uuid4()

        # When
        repository.get_by_id(job_id)

        # Then
        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        assert params['id'] == str(job_id)

    def test_get_all_returns_empty_list_when_no_jobs(self, mock_client, mock_session):
        # Given
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyJobRepository(mock_client)

        # When
        result = repository.get_all()

        # Then
        assert result == []

    def test_get_all_returns_all_jobs(self, mock_client, mock_session):
        # Given
        rows = [
            (
                str(uuid4()),
                JobType.GET_TRADES.value,
                JobStatus.DONE.value,
                '',
                1704067200.0,
                1704067201.0,
            ),
            (
                str(uuid4()),
                JobType.RUN_BACKTEST.value,
                JobStatus.RUNNING.value,
                'progressing',
                1704067300.0,
                1704067301.0,
            ),
        ]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = rows
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyJobRepository(mock_client)

        # When
        result = repository.get_all()

        # Then
        assert len(result) == 2
        assert result[0].job_type == JobType.GET_TRADES
        assert result[0].status == JobStatus.DONE
        assert result[1].job_type == JobType.RUN_BACKTEST
        assert result[1].status == JobStatus.RUNNING

    def test_get_all_passes_none_when_no_job_type_filter(self, mock_client, mock_session):
        # Given
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyJobRepository(mock_client)

        # When
        repository.get_all()

        # Then
        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        assert params['job_type'] is None

    def test_get_all_passes_job_type_value_when_filtering(self, mock_client, mock_session):
        # Given
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyJobRepository(mock_client)

        # When
        repository.get_all(job_type=JobType.RUN_BACKTEST)

        # Then
        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        assert params['job_type'] == 'run_backtest'
