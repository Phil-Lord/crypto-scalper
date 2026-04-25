from abc import ABC, abstractmethod

from data_system.models import Job, JobType


class JobRepository(ABC):
    @abstractmethod
    def add(self, job: Job) -> None:
        '''
        Inserts a job into the database.

        :param job: Job domain object to persist.
        '''
        pass

    @abstractmethod
    def update(self, job: Job) -> None:
        '''
        Updates an existing job in the database.

        :param job: Job domain object with updated fields. Must have a valid ID.
        '''
        pass

    @abstractmethod
    def get_by_id(self, job_id: str) -> Job | None:
        '''
        Fetches a job by its ID.

        :param job_id: The ID of the job to fetch.
        :return: The Job domain object with the specified ID, or None if not found.
        '''
        pass

    @abstractmethod
    def get_all(self, job_type: JobType | None = None) -> list[Job]:
        '''
        Fetches all jobs from the database.

        :param job_type: Optional filter by job type.
        :return: List of all Job domain objects, optionally filtered by job type.
        '''
        pass
