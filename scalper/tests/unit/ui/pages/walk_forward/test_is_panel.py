import asyncio

import pytest

from ui.pages.walk_forward.components import is_panel as is_panel_module
from utils import StudyDirection, StudySummary
from ui.pages.walk_forward.components.is_panel import (
    IsPanel,
    IsRunInputs,
    derive_run_inputs,
    validate_is_form,
)
from ui.pages.walk_forward.phase_mutex import PhaseMutex


def _summary(name: str) -> StudySummary:
    return StudySummary(
        name=name,
        pair='XXBTZGBP',
        strategy='SmaStrategy',
        trial_count=0,
        best_is=None,
        direction=StudyDirection.MAXIMIZE,
    )


@pytest.mark.ui
@pytest.mark.walk_forward_is_panel
class TestDeriveRunInputs:
    def test_decodes_canonical_study_name(self):
        result = derive_run_inputs(
            _summary('SmaStrategy_XXBTZGBP_20250101-20250401')
        )
        assert result == IsRunInputs(
            raw_pair='BTCGBP',
            strategy='SmaStrategy',
            start='2025-1-1-0-0-0',
            end='2025-4-1-0-0-0',
        )

    def test_returns_none_for_legacy_name_without_window(self):
        '''
        Older studies were named purely by ``Strategy_pair``. The panel must
        return ``None`` so the page can disable the button rather than
        passing garbage into ``start_in_sample``.
        '''
        assert derive_run_inputs(_summary('SmaStrategy_BTCGBP')) is None

    def test_returns_none_for_unknown_pair(self):
        assert derive_run_inputs(
            _summary('SmaStrategy_NOTAPAIR_20250101-20250401')
        ) is None

    def test_returns_none_for_unparseable_dates(self):
        assert derive_run_inputs(
            _summary('SmaStrategy_XXBTZGBP_notadate-20250401')
        ) is None

    def test_round_trips_with_create_study_name(self):
        '''
        The decoded inputs must reconstruct the same study name when fed
        back through ``utils.create_study_name`` — that's how
        ``start_in_sample`` resolves which study to extend.
        '''
        from utils import create_study_name, get_kraken_pair, get_second_timestamp, parse_datetime

        original = 'PrecisionTrendStrategy_XXBTZGBP_20240315-20240920'
        inputs = derive_run_inputs(_summary(original))
        assert inputs is not None

        rebuilt = create_study_name(
            inputs.strategy,
            get_kraken_pair(inputs.raw_pair),
            get_second_timestamp(*parse_datetime(inputs.start)),
            get_second_timestamp(*parse_datetime(inputs.end)),
        )
        assert rebuilt == original


@pytest.mark.ui
@pytest.mark.walk_forward_is_panel
class TestValidateIsForm:
    def test_returns_ints_for_valid_input(self):
        assert validate_is_form('100', '4') == (100, 4)

    def test_strips_whitespace(self):
        assert validate_is_form(' 50 ', '\t2\n') == (50, 2)

    @pytest.mark.parametrize('trials,workers', [('abc', '4'), ('10', 'x'), ('', '4'), (None, '4')])
    def test_rejects_non_integers(self, trials, workers):
        with pytest.raises(ValueError, match='must be integers'):
            validate_is_form(trials, workers)

    @pytest.mark.parametrize('trials,workers', [('0', '4'), ('10', '0'), ('-1', '4'), ('5', '-2')])
    def test_rejects_non_positive(self, trials, workers):
        with pytest.raises(ValueError, match='must be positive'):
            validate_is_form(trials, workers)


def _make_panel(
    mocker,
    selected: StudySummary | None = None,
    trials_value: str = '100',
    workers_value: str = '4',
) -> tuple[IsPanel, dict]:
    '''
    Build an :class:`IsPanel` with mock dependencies and a stubbed strip /
    inputs (so we exercise ``_on_start`` / ``_on_stop`` without going through
    :meth:`IsPanel.render`, which needs a NiceGUI client context).

    ``start_in_sample`` is patched to a sentinel — the panel passes its
    return value into ``mutex.start``, which is itself mocked, so the real
    coroutine never has to run.

    Returns the panel and a dict of the mocks for assertion access.
    '''
    if selected is None:
        selected = _summary('SmaStrategy_XXBTZGBP_20250101-20250401')
    phase_mutex = mocker.MagicMock(spec=PhaseMutex)
    phase_mutex.is_busy = False
    phase_mutex.is_active.return_value = False
    job_repo = mocker.MagicMock()
    set_running = mocker.MagicMock()
    # Replace ``start_in_sample`` with a plain ``MagicMock`` (not the default
    # ``AsyncMock`` autospec gives async functions) so calling it returns a
    # sentinel rather than a coroutine that pytest will flag as never awaited.
    fake_start = mocker.MagicMock(return_value='<coro-sentinel>')
    mocker.patch.object(is_panel_module, 'start_in_sample', fake_start)

    panel = IsPanel(
        phase_mutex=phase_mutex,
        get_selected_study=lambda: selected,
        job_repo=job_repo,
        set_running_study_name=set_running,
    )
    panel._strip = mocker.MagicMock()
    panel._trials_input = mocker.MagicMock(value=trials_value)
    panel._workers_input = mocker.MagicMock(value=workers_value)

    return panel, {
        'phase_mutex': phase_mutex,
        'job_repo': job_repo,
        'set_running': set_running,
        'strip': panel._strip,
        'selected': selected,
        'start_in_sample': fake_start,
    }


def _completed_task(result=None):
    async def _coro():
        return result
    return asyncio.create_task(_coro())


def _failing_task(exc: BaseException):
    async def _coro():
        raise exc
    return asyncio.create_task(_coro())


@pytest.mark.ui
@pytest.mark.walk_forward_is_panel
class TestOnStart:
    def test_returns_silently_when_no_study_selected(self, mocker):
        panel, deps = _make_panel(mocker, selected=None)
        # Override the lambda — _make_panel sets a default; replace it.
        panel._get_selected_study = lambda: None
        notify = mocker.patch.object(is_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        deps['phase_mutex'].start.assert_not_called()
        deps['set_running'].assert_not_called()
        notify.assert_not_called()

    def test_returns_silently_when_mutex_busy(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].is_busy = True
        notify = mocker.patch.object(is_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        deps['phase_mutex'].start.assert_not_called()
        notify.assert_not_called()

    def test_notifies_when_study_name_unparseable(self, mocker):
        '''
        Defensive against the disabled button being bypassed: if the study
        name does not match the canonical format, the panel notifies and
        bails rather than passing garbage into ``start_in_sample``.
        '''
        panel, deps = _make_panel(mocker, selected=_summary('legacy-name'))
        notify = mocker.patch.object(is_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        deps['phase_mutex'].start.assert_not_called()
        notify.assert_called_once()
        assert notify.call_args.kwargs['type'] == 'negative'
        assert 'legacy-name' in notify.call_args.args[0]

    def test_notifies_on_form_validation_error(self, mocker):
        panel, deps = _make_panel(mocker, trials_value='abc')
        notify = mocker.patch.object(is_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        deps['phase_mutex'].start.assert_not_called()
        notify.assert_called_once()
        assert notify.call_args.kwargs['type'] == 'negative'
        assert 'integers' in notify.call_args.args[0]

    def test_seeds_strip_with_split_trials(self, mocker):
        panel, deps = _make_panel(mocker, trials_value='10', workers_value='4')
        deps['phase_mutex'].start.side_effect = lambda phase, coro: _completed_task()
        mocker.patch.object(is_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        deps['strip'].show_workers.assert_called_once_with([3, 3, 2, 2])

    def test_sets_running_study_name_before_mutex_start(self, mocker):
        '''
        The page's phase-change listener fires synchronously inside
        ``mutex.start`` and re-renders the rail — so the running study name
        must already be set when ``start`` is called, otherwise the rail's
        running pill won't latch onto the right row.
        '''
        panel, deps = _make_panel(mocker)
        order: list[str] = []
        deps['set_running'].side_effect = lambda name: order.append(f'set:{name}')

        def fake_mutex_start(phase, coro):
            order.append(f'mutex.start:{phase}')
            return _completed_task()
        deps['phase_mutex'].start.side_effect = fake_mutex_start
        mocker.patch.object(is_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        assert order == [
            f'set:{deps["selected"].name}',
            'mutex.start:is',
        ]

    def test_passes_inputs_to_start_in_sample(self, mocker):
        '''
        The panel must hand the decoded run inputs (raw_pair, strategy,
        start, end, n_trials, n_workers) and the page's job repo to
        ``start_in_sample`` — that's how the IS subprocess reconstructs the
        study name to extend.
        '''
        panel, deps = _make_panel(mocker, trials_value='10', workers_value='4')
        deps['phase_mutex'].start.side_effect = lambda phase, coro: _completed_task()
        mocker.patch.object(is_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        deps['start_in_sample'].assert_called_once()
        call = deps['start_in_sample'].call_args
        assert call.args[0] == 'BTCGBP'
        assert call.args[1] == 'SmaStrategy'
        assert call.args[2] == '2025-1-1-0-0-0'
        assert call.args[3] == '2025-4-1-0-0-0'
        assert call.args[4] == 10
        assert call.args[5] == 4
        assert call.args[6] is deps['job_repo']

    def test_rolls_back_running_name_and_resets_strip_when_mutex_start_raises(
        self, mocker,
    ):
        '''
        If ``mutex.start`` raises (race against another phase), the panel
        must roll back the running-name latch and clear the strip's
        seeded tiles before notifying — otherwise the rail keeps a stale
        running pill and the next render shows phantom pending tiles.
        '''
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].start.side_effect = RuntimeError(
            'oos is already running'
        )
        notify = mocker.patch.object(is_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        assert deps['set_running'].call_args_list[-1].args == (None,)
        deps['strip'].reset_to_idle.assert_called_once()
        notify.assert_called_once()
        assert notify.call_args.kwargs['type'] == 'negative'
        assert 'oos is already running' in notify.call_args.args[0]

    def test_notifies_warning_when_task_cancelled(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].start.side_effect = (
            lambda phase, coro: _failing_task(asyncio.CancelledError())
        )
        notify = mocker.patch.object(is_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        notify.assert_called_once()
        assert notify.call_args.kwargs['type'] == 'warning'
        assert 'cancelled' in notify.call_args.args[0]

    def test_notifies_negative_when_task_raises(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].start.side_effect = (
            lambda phase, coro: _failing_task(RuntimeError('worker died'))
        )
        notify = mocker.patch.object(is_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        notify.assert_called_once()
        assert notify.call_args.kwargs['type'] == 'negative'
        assert 'worker died' in notify.call_args.args[0]

    def test_does_not_notify_on_clean_completion(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].start.side_effect = lambda phase, coro: _completed_task()
        notify = mocker.patch.object(is_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        notify.assert_not_called()


@pytest.mark.ui
@pytest.mark.walk_forward_is_panel
class TestOnStop:
    def test_returns_silently_when_not_active(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].is_active.return_value = False
        confirm = mocker.patch.object(is_panel_module, 'confirm_dialog')

        asyncio.run(panel._on_stop())

        confirm.assert_not_called()
        deps['phase_mutex'].cancel.assert_not_called()

    def test_cancels_when_user_confirms(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].is_active.return_value = True

        async def fake_confirm(**kwargs):
            return True
        mocker.patch.object(is_panel_module, 'confirm_dialog', side_effect=fake_confirm)

        asyncio.run(panel._on_stop())

        deps['phase_mutex'].cancel.assert_called_once()

    def test_does_not_cancel_when_user_declines(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].is_active.return_value = True

        async def fake_confirm(**kwargs):
            return False
        mocker.patch.object(is_panel_module, 'confirm_dialog', side_effect=fake_confirm)

        asyncio.run(panel._on_stop())

        deps['phase_mutex'].cancel.assert_not_called()
