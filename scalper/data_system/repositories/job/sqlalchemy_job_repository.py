import logging

from data_system.clients import SQLAlchemyClient
from data_system.repositories import JobRepository
from data_system.models import Job, JobType

logger = logging.getLogger(__name__)


class SQLAlchemyJobRepository(JobRepository):
    def __init__(self, client: SQLAlchemyClient) -> None:
        self.client = client

    def add(self, job: Job) -> None:
        with self.client.session() as session:
            session.add(job)

    def update(self, job: Job) -> None:
        with self.client.session() as session:
            session.merge(job)

    def get_by_id(self, job_id: str) -> Job | None:
        with self.client.session() as session:
            job = session.get(Job, job_id)

            # Detach from the session before it closes to prevent error on attribute access
            if job is not None:
                session.expunge(job)
            return job

    def get_all(self, job_type: JobType | None = None) -> list[Job]:
        with self.client.session() as session:
            query = session.query(Job)
            if job_type is not None:
                query = query.filter(Job.job_type == job_type)
            jobs = query.all()

            # Detach from the session before it closes to prevent error on attribute access
            session.expunge_all(jobs)
            return jobs
