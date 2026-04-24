import asyncio
from unittest.mock import MagicMock

import pytest

from core.job_runner import run_in_thread, run_subprocess
from data_system.models.job_model import Job, JobStatus, JobType
from data_system.repositories.job.job_repository import JobRepository


class _MockStdoutStream:
    '''Async-iterable mock for a subprocess stdout stream.'''
    def __init__(self, lines: list[bytes]):
        self._lines = iter(lines)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._lines)
        except StopIteration:
            raise StopAsyncIteration


class _MockProc:
    def __init__(self, returncode: int = 0, lines: list[bytes] | None = None):
        self.returncode = returncode
        self.stdout = _MockStdoutStream(lines or [])

    async def wait(self):
        return self.returncode


@pytest.mark.core
@pytest.mark.job_runner
class TestRunInThread:
    @pytest.fixture
    def job(self) -> Job:
        return Job(job_type=JobType.GET_TRADES)

    @pytest.fixture
    def mock_repo(self, mocker) -> JobRepository:
        return mocker.MagicMock(spec=JobRepository)

    def test_returns_fn_result(self, mock_repo, job: Job):
        def fn(x: int, y: int) -> int:
            return x + y

        result = asyncio.run(run_in_thread(mock_repo, job, fn, 2, 3))

        assert result == 5

    def test_marks_job_running_then_done_on_success(self, mock_repo, job: Job):
        statuses: list[JobStatus] = []

        def record_add(j: Job) -> None:
            statuses.append(j.status)

        def record_update(j: Job) -> None:
            statuses.append(j.status)

        mock_repo.add.side_effect = record_add
        mock_repo.update.side_effect = record_update

        asyncio.run(run_in_thread(mock_repo, job, lambda: 'ok'))

        assert statuses == [JobStatus.RUNNING, JobStatus.DONE]
        assert job.status == JobStatus.DONE

    def test_persists_running_status_before_executing_fn(self, mock_repo, job: Job):
        observed_status: list[JobStatus] = []

        def fn() -> None:
            observed_status.append(job.status)

        asyncio.run(run_in_thread(mock_repo, job, fn))

        assert observed_status == [JobStatus.RUNNING]
        mock_repo.add.assert_called_once()

    def test_marks_job_error_when_fn_raises(self, mock_repo, job: Job):
        def fn() -> None:
            raise RuntimeError('boom')

        with pytest.raises(RuntimeError, match='boom'):
            asyncio.run(run_in_thread(mock_repo, job, fn))

        assert job.status == JobStatus.ERROR
        assert job.message == 'boom'
        mock_repo.update.assert_called_once()

    def test_passes_args_through_to_fn(self, mock_repo, job: Job):
        fn = MagicMock(return_value='done')

        asyncio.run(run_in_thread(mock_repo, job, fn, 'a', 'b', 'c'))

        fn.assert_called_once_with('a', 'b', 'c')


@pytest.mark.core
@pytest.mark.job_runner
class TestRunSubprocess:
    @pytest.fixture
    def job(self) -> Job:
        return Job(job_type=JobType.RUN_BACKTEST)

    @pytest.fixture
    def mock_repo(self, mocker) -> JobRepository:
        return mocker.MagicMock(spec=JobRepository)

    def _patch_subprocess(self, mocker, proc: _MockProc):
        async def _create(*args, **kwargs):
            return proc

        mocker.patch('core.job_runner.asyncio.create_subprocess_exec', side_effect=_create)

    def test_marks_job_done_when_subprocess_exits_zero(self, mocker, mock_repo, job: Job):
        self._patch_subprocess(mocker, _MockProc(returncode=0, lines=[]))

        asyncio.run(run_subprocess(mock_repo, job, ['echo', 'hi']))

        assert job.status == JobStatus.DONE

    def test_marks_job_error_when_subprocess_exits_non_zero(self, mocker, mock_repo, job: Job):
        self._patch_subprocess(mocker, _MockProc(returncode=1, lines=[]))

        asyncio.run(run_subprocess(mock_repo, job, ['false']))

        assert job.status == JobStatus.ERROR

    def test_persists_running_status_before_streaming(self, mocker, mock_repo, job: Job):
        proc = _MockProc(returncode=0, lines=[])
        self._patch_subprocess(mocker, proc)

        asyncio.run(run_subprocess(mock_repo, job, ['echo', 'hi']))

        # add is called once up front with RUNNING; update is called at least once
        # with the terminal status after proc exits.
        mock_repo.add.assert_called_once()
        assert mock_repo.update.call_count >= 1

    def test_streams_stdout_lines_into_job_message(self, mocker, mock_repo, job: Job):
        proc = _MockProc(returncode=0, lines=[b'line 1\n', b'line 2\n'])
        self._patch_subprocess(mocker, proc)

        asyncio.run(run_subprocess(mock_repo, job, ['fake']))

        assert job.message == 'line 2'

    def test_invokes_on_progress_callback_for_each_line(self, mocker, mock_repo, job: Job):
        proc = _MockProc(returncode=0, lines=[b'a\n', b'b\n', b'c\n'])
        self._patch_subprocess(mocker, proc)
        on_progress = MagicMock()

        asyncio.run(run_subprocess(mock_repo, job, ['fake'], on_progress=on_progress))

        assert on_progress.call_count == 3
        assert [call.args[0] for call in on_progress.call_args_list] == ['a', 'b', 'c']

    def test_marks_job_error_when_subprocess_start_fails(self, mocker, mock_repo, job: Job):
        async def _fail(*args, **kwargs):
            raise OSError('cannot spawn')

        mocker.patch('core.job_runner.asyncio.create_subprocess_exec', side_effect=_fail)

        with pytest.raises(OSError, match='cannot spawn'):
            asyncio.run(run_subprocess(mock_repo, job, ['fake']))

        assert job.status == JobStatus.ERROR
        assert job.message == 'cannot spawn'
