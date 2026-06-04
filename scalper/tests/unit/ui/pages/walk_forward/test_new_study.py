import asyncio

import pytest

from ui.pages.walk_forward import new_study as new_study_module
from ui.pages.walk_forward.components.new_study_dialog import NewStudyForm
from utils import get_second_timestamp, parse_datetime


def _form(**overrides) -> NewStudyForm:
    base = dict(
        pair='BTCGBP',
        strategy='SmaStrategy',
        start='2024-1-1-0-0-0',
        end='2026-1-1-0-0-0',
        n_trials=10,
        n_workers=2,
    )
    base.update(overrides)
    return NewStudyForm(**base)


def _completed_task(result=None):
    async def _coro():
        return result
    return asyncio.create_task(_coro())


@pytest.mark.ui
@pytest.mark.walk_forward_new_study
class TestStartInSampleFromForm:
    def _make_page(self, mocker):
        page = mocker.MagicMock()
        page.phase_mutex.is_busy = False
        # ``_rerender_all`` is now a coroutine the flow awaits, and
        # ``_can_render`` gates the post-run notify (truthy by default).
        page._rerender_all = mocker.AsyncMock()
        page._can_render.return_value = True
        # Build the task lazily inside the running loop (start is called from
        # within ``asyncio.run``), not at fixture-setup time.
        page.phase_mutex.start.side_effect = lambda phase, coro: _completed_task([])
        return page

    def test_passes_second_timestamps_not_raw_text(self, mocker):
        '''
        Regression: the form preserves the user's text datetimes verbatim, but
        ``start_in_sample`` expects float second-timestamps. Forwarding the raw
        strings reaches the SQL ``timestamp BETWEEN`` query, which matches no
        rows and kills the worker with 'No trades found' before the study is
        created — the run dies silently.
        '''
        page = self._make_page(mocker)
        start_in_sample = mocker.patch.object(
            new_study_module, 'start_in_sample', return_value='<coro-sentinel>'
        )
        mocker.patch.object(new_study_module, 'split_trials', return_value=[5, 5])

        asyncio.run(new_study_module.start_in_sample_from_form(page, _form()))

        # positional: pair, strategy, start, end, n_trials, n_workers, ...
        _, _, start_arg, end_arg, *_ = start_in_sample.call_args.args
        assert start_arg == get_second_timestamp(*parse_datetime('2024-1-1-0-0-0'))
        assert end_arg == get_second_timestamp(*parse_datetime('2026-1-1-0-0-0'))
        assert isinstance(start_arg, float)
        assert isinstance(end_arg, float)

    def test_notifies_when_the_run_fails(self, mocker):
        '''
        A worker exiting non-zero (e.g. genuinely data-less range) now raises
        out of the awaited task, so the user gets a notification rather than
        the panels silently clearing.
        '''
        page = self._make_page(mocker)
        page.phase_mutex.start.side_effect = lambda phase, coro: _failing_task(
            RuntimeError('Subprocess exited with code 1: No trades found')
        )
        mocker.patch.object(
            new_study_module, 'start_in_sample', return_value='<coro-sentinel>'
        )
        mocker.patch.object(new_study_module, 'split_trials', return_value=[5, 5])
        notify = mocker.patch.object(new_study_module.ui, 'notify')

        asyncio.run(new_study_module.start_in_sample_from_form(page, _form()))

        notify.assert_called_once()
        assert notify.call_args.kwargs['type'] == 'negative'
        assert 'No trades found' in notify.call_args.args[0]


def _failing_task(exc: BaseException):
    async def _coro():
        raise exc
    return asyncio.create_task(_coro())
