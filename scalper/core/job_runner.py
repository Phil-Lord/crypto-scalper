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
    job = job.update(status=JobStatus.RUNNING)
    job_repo.add(job)
    try:
        result = await asyncio.to_thread(fn, *args)
        job = job.update(status=JobStatus.DONE)
        job_repo.update(job)
        return result
    except Exception as e:
        job = job.update(status=JobStatus.ERROR, message=str(e))
        job_repo.update(job)
        raise


async def run_subprocess(
    job_repo: JobRepository,
    job: Job,
    cmd: list[str],
    on_progress: Callable[[str], None] | None = None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    terminate_grace_seconds: float = 5.0,
) -> None:
    '''
    Spawn a separate OS process which runs independently of the UI.

    - For long-running, CPU-bound tasks which need to survive if the UI crashes.
    - Streams stdout lines back to the UI via the ``Job.message`` field.
    - Cooperates with ``asyncio.CancelledError``: on cancellation the child is sent
      ``SIGTERM``, given ``terminate_grace_seconds`` to exit, then ``SIGKILL``-ed
      if still alive. The job is persisted as ``ERROR`` with a ``cancelled`` message
      and ``CancelledError`` is re-raised so the caller's task remains cancelled.

    :param job_repo: Repository used to persist job lifecycle transitions.
    :param job: Initial pending job.
    :param cmd: Argv list passed to ``asyncio.create_subprocess_exec``.
    :param on_progress: Optional callback invoked with each decoded stdout line.
    :param cwd: Optional working directory for the subprocess.
    :param env: Optional environment for the subprocess. ``None`` inherits the
        parent's environment.
    :param terminate_grace_seconds: Seconds to wait after ``terminate()`` before
        escalating to ``kill()``.
    '''
    job = job.update(status=JobStatus.RUNNING)
    job_repo.add(job)

    proc: asyncio.subprocess.Process | None = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
            env=env,
        )

        last_update = 0.0
        async for line in proc.stdout:
            job = job.update(message=line.decode().strip())  # stream tqdm progress
            if on_progress:
                on_progress(job.message)
            now = time.monotonic()
            if now - last_update > 1.0:  # throttle DB updates to max 1 per second
                job_repo.update(job)
                last_update = now

        await proc.wait()
        job = job.update(status=JobStatus.DONE if proc.returncode == 0 else JobStatus.ERROR)
        job_repo.update(job)
    except asyncio.CancelledError:
        if proc is not None:
            await _terminate_process(proc, terminate_grace_seconds)
        job = job.update(status=JobStatus.ERROR, message='cancelled')
        job_repo.update(job)
        raise
    except Exception as e:
        job = job.update(status=JobStatus.ERROR, message=str(e))
        job_repo.update(job)
        raise


async def _terminate_process(
    proc: asyncio.subprocess.Process, grace_seconds: float
) -> None:
    '''
    Send SIGTERM, wait up to ``grace_seconds`` for the process to exit, then SIGKILL.

    Swallows ``ProcessLookupError`` since the process may have already exited.
    '''
    if proc.returncode is not None:
        return

    try:
        proc.terminate()
    except ProcessLookupError:
        return

    try:
        await asyncio.wait_for(proc.wait(), timeout=grace_seconds)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            return
        await proc.wait()
