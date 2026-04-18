import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum


class JobStatus(Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    DONE = 'done'
    ERROR = 'error'


@dataclass
class Job:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: JobStatus = JobStatus.PENDING
    message: str = ''


async def run_in_thread(job: Job, fn, *args):
    '''
    Run an async blocking function in a separate thread.

    - Ideal for I/O-bound and short CPU-bound tasks.
    - The task lives and dies with the app process.
    - Progress updates are streamed back to the UI via the Job.message field.
    '''
    job.status = JobStatus.RUNNING
    try:
        result = await asyncio.to_thread(fn, *args)
        job.status = JobStatus.DONE
        return result
    except Exception as e:
        job.status = JobStatus.ERROR
        job.message = str(e)
        raise


async def run_subprocess(job: Job, cmd: list[str]):
    '''
    Spawn a separate OS process which runs independently of the UI.

    - This is for long-running, CPU-bound tasks which need to survive if the UI crashes.
    - The subprocess streams progress updates back to the UI via the Job.message field.
    '''
    job.status = JobStatus.RUNNING
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        async for line in proc.stdout:
            job.message = line.decode().strip()  # stream tqdm progress
        await proc.wait()
        job.status = JobStatus.DONE if proc.returncode == 0 else JobStatus.ERROR
    except Exception as e:
        job.status = JobStatus.ERROR
        job.message = str(e)
