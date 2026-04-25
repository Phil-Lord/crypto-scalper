import asyncio
import time
from collections.abc import Callable
from typing import Any

from data_system import Job, JobRepository, JobStatus


async def run_in_thread(job_repo: JobRepository, job: Job, fn: Callable[..., Any], *args) -> Any:
    '''
    Run a blocking function in a separate thread.

    - Ideal for I/O-bound and short CPU-bound tasks.
    - The task lives and dies with the app process.
    - Progress updates are streamed back to the UI via the Job.message field.
    '''
    job.update(status=JobStatus.RUNNING)
    job_repo.add(job)
    try:
        result = await asyncio.to_thread(fn, *args)
        job.update(status=JobStatus.DONE)
        job_repo.update(job)
        return result
    except Exception as e:
        job.update(status=JobStatus.ERROR, message=str(e))
        job_repo.update(job)
        raise


async def run_subprocess(
    job_repo: JobRepository,
    job: Job,
    cmd: list[str],
    on_progress: Callable[[str], None] | None = None,
) -> None:
    '''
    Spawn a separate OS process which runs independently of the UI.

    - This is for long-running, CPU-bound tasks which need to survive if the UI crashes.
    - The subprocess streams progress updates back to the UI via the Job.message field.
    '''
    job.update(status=JobStatus.RUNNING)
    job_repo.add(job)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        last_update = 0.0
        async for line in proc.stdout:
            job.update(message=line.decode().strip())  # stream tqdm progress
            if on_progress:
                on_progress(job.message)
            now = time.monotonic()
            if now - last_update > 1.0:  # throttle DB updates to max 1 per second
                job_repo.update(job)
                last_update = now

        await proc.wait()
        job.update(status=JobStatus.DONE if proc.returncode == 0 else JobStatus.ERROR)
        job_repo.update(job)
    except Exception as e:
        job.update(status=JobStatus.ERROR, message=str(e))
        job_repo.update(job)
        raise
