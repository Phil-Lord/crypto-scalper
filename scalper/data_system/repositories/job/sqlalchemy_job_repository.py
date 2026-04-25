from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Row, text

from data_system.clients import SQLAlchemyClient
from data_system.models import Job, JobStatus, JobType
from data_system.repositories import JobRepository


class SQLAlchemyJobRepository(JobRepository):
    def __init__(self, client: SQLAlchemyClient) -> None:
        self.client = client

    def add(self, job: Job) -> None:
        with self.client.session() as session:
            query = text('''
                INSERT INTO jobs (id, job_type, status, message, created_at, updated_at)
                VALUES (:id, :job_type, :status, :message, :created_at, :updated_at)
            ''')
            session.execute(query, self._to_record(job))

    def update(self, job: Job) -> None:
        with self.client.session() as session:
            query = text('''
                UPDATE jobs
                SET status = :status, message = :message, updated_at = :updated_at
                WHERE id = :id
            ''')
            session.execute(query, self._to_record(job))

    def get_by_id(self, job_id: str) -> Job | None:
        with self.client.session() as session:
            result = session.execute(
                text('SELECT * FROM jobs WHERE id = :id'),
                {'id': str(job_id)},
            )
            record = result.fetchone()
            return self._to_job(record) if record else None

    def get_all(self, job_type: JobType | None = None) -> list[Job]:
        with self.client.session() as session:
            result = session.execute(
                text('''
                    SELECT * FROM jobs
                    WHERE (:job_type IS NULL OR job_type = :job_type)
                    ORDER BY created_at DESC
                '''),
                {'job_type': job_type.value if job_type else None},
            )
            return [self._to_job(row) for row in result.fetchall()]

    def _to_record(self, job: Job) -> dict:
        return {
            'id': str(job.id),
            'job_type': job.job_type.value,
            'status': job.status.value,
            'message': job.message,
            'created_at': job.created_at.timestamp(),
            'updated_at': job.updated_at.timestamp(),
        }

    def _to_job(self, record: Row) -> Job:
        return Job(
            id=UUID(record[0]),
            job_type=JobType(record[1]),
            status=JobStatus(record[2]),
            message=record[3] or '',
            created_at=datetime.fromtimestamp(record[4], tz=timezone.utc),
            updated_at=datetime.fromtimestamp(record[5], tz=timezone.utc),
        )
