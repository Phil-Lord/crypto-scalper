from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class JobType(str, Enum):
    GET_TRADES = 'get_trades'
    FETCH_TRADES = 'fetch_trades'
    RUN_BACKTEST = 'run_backtest'


class JobStatus(str, Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    DONE = 'done'
    ERROR = 'error'


@dataclass
class Job:
    '''
    Dataclass representing a background job/task.

    Attributes:
        job_type (JobType): The job type, e.g., 'get_trades, 'run_backtest', etc.
        id (UUID): Unique identifier for the job, auto-generated as a UUID.
        status (JobStatus): Current status of the job, default is PENDING.
        message (str): Optional message for status updates or error details.
        created_at (datetime): Timestamp when the job was created, default is now.
        updated_at (datetime): Timestamp when the job was last updated, default is now.

    Database Mapping:
        - id: TEXT PRIMARY KEY (UUID stored as string)
        - job_type: TEXT NOT NULL
        - status: TEXT NOT NULL DEFAULT 'pending'
        - message: TEXT
        - created_at: REAL NOT NULL
        - updated_at: REAL NOT NULL
    '''
    job_type: JobType
    id: UUID = field(default_factory=uuid4)
    status: JobStatus = JobStatus.PENDING
    message: str = ''
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
