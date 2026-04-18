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
