from datetime import datetime, timezone
from uuid import UUID

import pytest

from data_system.models.job_model import Job, JobStatus, JobType


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.job_model
class TestJob:
    @pytest.fixture
    def sample_job(self) -> Job:
        return Job(job_type=JobType.GET_TRADES)

    def test_creates_job_with_required_fields(self, sample_job: Job):
        assert sample_job.job_type == JobType.GET_TRADES

    def test_id_is_auto_generated_uuid(self, sample_job: Job):
        assert isinstance(sample_job.id, UUID)

    def test_two_jobs_have_different_ids(self):
        job1 = Job(job_type=JobType.GET_TRADES)
        job2 = Job(job_type=JobType.GET_TRADES)
        assert job1.id != job2.id

    def test_id_can_be_set_explicitly(self):
        # Given
        custom_id = UUID('12345678-1234-5678-1234-567812345678')

        # When
        job = Job(job_type=JobType.GET_TRADES, id=custom_id)

        # Then
        assert job.id == custom_id

    def test_status_defaults_to_pending(self, sample_job: Job):
        assert sample_job.status == JobStatus.PENDING

    def test_message_defaults_to_empty_string(self, sample_job: Job):
        assert sample_job.message == ''

    def test_created_at_defaults_to_current_utc_time(self):
        # Given
        before = datetime.now(timezone.utc)

        # When
        job = Job(job_type=JobType.GET_TRADES)
        after = datetime.now(timezone.utc)

        # Then
        assert isinstance(job.created_at, datetime)
        assert job.created_at.tzinfo is not None
        assert before <= job.created_at <= after

    def test_updated_at_defaults_to_current_utc_time(self):
        # Given
        before = datetime.now(timezone.utc)

        # When
        job = Job(job_type=JobType.GET_TRADES)
        after = datetime.now(timezone.utc)

        # Then
        assert isinstance(job.updated_at, datetime)
        assert job.updated_at.tzinfo is not None
        assert before <= job.updated_at <= after

    def test_job_is_frozen(self, sample_job: Job):
        with pytest.raises(AttributeError):
            sample_job.status = JobStatus.RUNNING

    def test_update_returns_new_instance(self, sample_job: Job):
        updated = sample_job.update(status=JobStatus.RUNNING)
        assert updated is not sample_job
        assert sample_job.status == JobStatus.PENDING

    def test_update_sets_status(self, sample_job: Job):
        updated = sample_job.update(status=JobStatus.RUNNING)
        assert updated.status == JobStatus.RUNNING

    def test_update_sets_message(self, sample_job: Job):
        updated = sample_job.update(message='fetching page 3')
        assert updated.message == 'fetching page 3'

    def test_update_sets_status_and_message_together(self, sample_job: Job):
        updated = sample_job.update(status=JobStatus.ERROR, message='boom')
        assert updated.status == JobStatus.ERROR
        assert updated.message == 'boom'

    def test_update_refreshes_updated_at(self, sample_job: Job):
        # Given
        original_updated_at = sample_job.updated_at

        # When
        updated = sample_job.update(status=JobStatus.RUNNING)

        # Then
        assert updated.updated_at >= original_updated_at
        assert updated.updated_at.tzinfo is not None

    def test_update_refreshes_updated_at_even_with_no_args(self, sample_job: Job):
        # Given
        original_updated_at = sample_job.updated_at

        # When
        updated = sample_job.update()

        # Then
        assert updated.updated_at >= original_updated_at

    def test_update_does_not_overwrite_status_when_none(self, sample_job: Job):
        # Given
        running = sample_job.update(status=JobStatus.RUNNING)

        # When
        updated = running.update(message='progress update')

        # Then
        assert updated.status == JobStatus.RUNNING
        assert updated.message == 'progress update'

    def test_update_does_not_overwrite_message_when_none(self, sample_job: Job):
        # Given
        with_message = sample_job.update(message='initial message')

        # When
        updated = with_message.update(status=JobStatus.DONE)

        # Then
        assert updated.status == JobStatus.DONE
        assert updated.message == 'initial message'

    def test_update_allows_empty_string_message(self, sample_job: Job):
        # Given
        with_message = sample_job.update(message='something')

        # When
        cleared = with_message.update(message='')

        # Then
        assert cleared.message == ''

    def test_update_preserves_id_and_created_at(self, sample_job: Job):
        updated = sample_job.update(status=JobStatus.RUNNING)
        assert updated.id == sample_job.id
        assert updated.created_at == sample_job.created_at
        assert updated.job_type == sample_job.job_type


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.job_model
class TestJobType:
    def test_get_trades_value(self):
        assert JobType.GET_TRADES.value == 'get_trades'

    def test_fetch_trades_value(self):
        assert JobType.FETCH_TRADES.value == 'fetch_trades'

    def test_run_backtest_value(self):
        assert JobType.RUN_BACKTEST.value == 'run_backtest'

    def test_is_string_enum(self):
        assert isinstance(JobType.GET_TRADES, str)
        assert JobType.GET_TRADES == 'get_trades'


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.job_model
class TestJobStatus:
    def test_pending_value(self):
        assert JobStatus.PENDING.value == 'pending'

    def test_running_value(self):
        assert JobStatus.RUNNING.value == 'running'

    def test_done_value(self):
        assert JobStatus.DONE.value == 'done'

    def test_error_value(self):
        assert JobStatus.ERROR.value == 'error'

    def test_is_string_enum(self):
        assert isinstance(JobStatus.PENDING, str)
        assert JobStatus.PENDING == 'pending'
