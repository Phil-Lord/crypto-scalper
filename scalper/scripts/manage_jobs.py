import logging
from datetime import datetime, timezone

import questionary

from data_system import Job, JobRepository, JobStatus, JobType, SQLAlchemyClient, SQLAlchemyJobRepository
from utils import load_env, LOG_FORMAT

load_env()
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def manage_jobs():
    repository = SQLAlchemyJobRepository(SQLAlchemyClient())
    action = questionary.select('Action:', choices=['add', 'update', 'get_by_id', 'get_all']).ask()

    if action == 'add':
        add(repository)
    elif action == 'update':
        update(repository)
    elif action == 'get_by_id':
        get_by_id(repository)
    elif action == 'get_all':
        get_all(repository)


def add(repository: JobRepository):
    job_type = questionary.select('Job Type:', choices=[type.value for type in JobType]).ask()
    job = Job(job_type=JobType(job_type))
    repository.add(job)
    print('Added job:', job)


def update(repository: JobRepository):
    job_id = questionary.text('Job ID:').ask()
    job = repository.get_by_id(job_id)
    if not job:
        print('Job not found')
        return

    status = questionary.select('Status:', choices=[status.value for status in JobStatus]).ask()
    message = questionary.text('Message (optional):').ask()

    job.status = JobStatus(status)
    job.message = message
    job.updated_at = datetime.now(timezone.utc)
    repository.update(job)
    print('Updated job:', job)


def get_by_id(repository: JobRepository):
    job_id = questionary.text('Job ID:').ask()
    job = repository.get_by_id(job_id)
    if job:
        print('Retrieved job:', job)
    else:
        print('Job not found')


def get_all(repository: JobRepository):
    job_type = questionary.select(
        'Filter by Job Type (optional):', choices=['All'] + [type.value for type in JobType]).ask()
    job_type_enum = JobType(job_type) if job_type != 'All' else None
    jobs = repository.get_all(job_type_enum)
    print(f'Retrieved {len(jobs)} job(s):')
    for job in jobs:
        print(job)


if __name__ == '__main__':
    manage_jobs()
