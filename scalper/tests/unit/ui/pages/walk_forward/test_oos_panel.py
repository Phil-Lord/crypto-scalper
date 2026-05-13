import asyncio

import pytest

from core import StreamEvent
from ui.models.walk_forward import StudyDirection, StudySummary
from ui.pages.walk_forward.components import oos_panel as oos_panel_module
from ui.pages.walk_forward.components.oos_panel import (
    OosPanel,
    OosRunInputs,
    derive_window_key,
    validate_oos_form,
)
from ui.pages.walk_forward.components.window_tabs import WindowKey
from ui.pages.walk_forward.phase_mutex import PhaseMutex


def _summary(name: str = 'SmaStrategy_XXBTZGBP_20250101-20250401') -> StudySummary:
    return StudySummary(
        name=name,
        pair='XXBTZGBP',
        strategy='SmaStrategy',
        trial_count=10,
        best_is=1.5,
        direction=StudyDirection.MAXIMIZE,
    )


@pytest.mark.ui
@pytest.mark.walk_forward_oos_panel
class TestValidateOosForm:
    def test_returns_inputs_for_valid_input(self):
        inputs = validate_oos_form('2025-1-1-0-0-0', '2025-4-1-0-0-0', '25', '4')
        assert inputs == OosRunInputs(
            start='2025-1-1-0-0-0',
            end='2025-4-1-0-0-0',
            top_n=25,
            n_workers=4,
        )

    def test_strips_whitespace_around_dates(self):
        inputs = validate_oos_form(' 2025-1-1-0-0-0 ', '2025-4-1-0-0-0', '25', '4')
        assert inputs.start == '2025-1-1-0-0-0'

    @pytest.mark.parametrize('start,end', [
        ('', '2025-4-1-0-0-0'),
        ('2025-1-1-0-0-0', ''),
        (None, '2025-4-1-0-0-0'),
        ('2025-1-1-0-0-0', None),
    ])
    def test_rejects_blank_dates(self, start, end):
        with pytest.raises(ValueError, match='required'):
            validate_oos_form(start, end, '25', '4')

    def test_rejects_unparseable_start(self):
        with pytest.raises(ValueError, match='start is not parseable'):
            validate_oos_form('not-a-date', '2025-4-1-0-0-0', '25', '4')

    def test_rejects_unparseable_end(self):
        with pytest.raises(ValueError, match='end is not parseable'):
            validate_oos_form('2025-1-1-0-0-0', 'not-a-date', '25', '4')

    @pytest.mark.parametrize('top_n,workers', [
        ('abc', '4'), ('25', 'x'), ('', '4'), (None, '4'),
    ])
    def test_rejects_non_integer_counts(self, top_n, workers):
        with pytest.raises(ValueError, match='must be integers'):
            validate_oos_form('2025-1-1-0-0-0', '2025-4-1-0-0-0', top_n, workers)

    @pytest.mark.parametrize('top_n,workers', [
        ('0', '4'), ('25', '0'), ('-1', '4'), ('25', '-2'),
    ])
    def test_rejects_non_positive_counts(self, top_n, workers):
        with pytest.raises(ValueError, match='must be positive'):
            validate_oos_form('2025-1-1-0-0-0', '2025-4-1-0-0-0', top_n, workers)


@pytest.mark.ui
@pytest.mark.walk_forward_oos_panel
class TestDeriveWindowKey:
    def test_converts_text_dates_to_timestamps(self):
        key = derive_window_key('2025-1-1-0-0-0', '2025-4-1-0-0-0')
        # Both fields are floats (Unix seconds) and ordered start < end.
        assert isinstance(key[0], float)
        assert isinstance(key[1], float)
        assert key[0] < key[1]


def _make_panel(
    mocker,
    selected: StudySummary | None = None,
    start_value: str = '2025-1-1-0-0-0',
    end_value: str = '2025-4-1-0-0-0',
    top_n_value: str = '25',
    workers_value: str = '4',
) -> tuple[OosPanel, dict]:
    '''
    Build an :class:`OosPanel` with mock dependencies and stubbed input
    widgets, so we exercise ``_on_start`` / ``_on_stop`` without going
    through :meth:`OosPanel.render` (which needs a NiceGUI client context).

    ``start_out_of_sample`` is patched to a sentinel and ``mutex.start``
    is itself mocked, so the real coroutine never has to run.
    '''
    if selected is None:
        selected = _summary()
    phase_mutex = mocker.MagicMock(spec=PhaseMutex)
    phase_mutex.is_busy = False
    phase_mutex.is_active.return_value = False
    job_repo = mocker.MagicMock()
    oos_repo = mocker.MagicMock()
    set_running = mocker.MagicMock()
    fake_start = mocker.MagicMock(return_value='<coro-sentinel>')
    mocker.patch.object(oos_panel_module, 'start_out_of_sample', fake_start)

    panel = OosPanel(
        phase_mutex=phase_mutex,
        get_selected_study=lambda: selected,
        oos_repo=oos_repo,
        job_repo=job_repo,
        set_running_study_name=set_running,
    )
    panel._start_input = mocker.MagicMock(value=start_value)
    panel._end_input = mocker.MagicMock(value=end_value)
    panel._top_n_input = mocker.MagicMock(value=top_n_value)
    panel._workers_input = mocker.MagicMock(value=workers_value)
    # Skip the in-panel re-render — _on_start calls self.render(self._container)
    # on success, and the real render needs a NiceGUI client.
    mocker.patch.object(panel, 'render')

    return panel, {
        'phase_mutex': phase_mutex,
        'job_repo': job_repo,
        'oos_repo': oos_repo,
        'set_running': set_running,
        'selected': selected,
        'start_out_of_sample': fake_start,
        'render': panel.render,
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
@pytest.mark.walk_forward_oos_panel
class TestOnStart:
    def test_returns_silently_when_no_study_selected(self, mocker):
        panel, deps = _make_panel(mocker)
        panel._get_selected_study = lambda: None
        notify = mocker.patch.object(oos_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        deps['phase_mutex'].start.assert_not_called()
        deps['set_running'].assert_not_called()
        notify.assert_not_called()

    def test_returns_silently_when_mutex_busy(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].is_busy = True
        notify = mocker.patch.object(oos_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        deps['phase_mutex'].start.assert_not_called()
        notify.assert_not_called()

    def test_notifies_on_form_validation_error(self, mocker):
        panel, deps = _make_panel(mocker, top_n_value='abc')
        notify = mocker.patch.object(oos_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        deps['phase_mutex'].start.assert_not_called()
        notify.assert_called_once()
        assert notify.call_args.kwargs['type'] == 'negative'
        assert 'integers' in notify.call_args.args[0]

    def test_sets_running_study_name_before_mutex_start(self, mocker):
        '''
        The page's phase-change listener fires synchronously inside
        ``mutex.start`` and re-renders the rail — so the running study
        name must already be set when ``start`` is called, otherwise the
        rail's running pill won't latch onto the right row.
        '''
        panel, deps = _make_panel(mocker)
        order: list[str] = []
        deps['set_running'].side_effect = lambda name: order.append(f'set:{name}')

        def fake_mutex_start(phase, coro):
            order.append(f'mutex.start:{phase}')
            return _completed_task()
        deps['phase_mutex'].start.side_effect = fake_mutex_start
        mocker.patch.object(oos_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        assert order == [
            f'set:{deps["selected"].name}',
            'mutex.start:oos',
        ]

    def test_passes_inputs_to_start_out_of_sample(self, mocker):
        panel, deps = _make_panel(
            mocker, top_n_value='10', workers_value='3',
        )
        deps['phase_mutex'].start.side_effect = lambda phase, coro: _completed_task()
        mocker.patch.object(oos_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        deps['start_out_of_sample'].assert_called_once()
        call = deps['start_out_of_sample'].call_args
        assert call.args[0] == deps['selected'].name
        assert call.args[1] == 10
        assert call.args[2] == '2025-1-1-0-0-0'
        assert call.args[3] == '2025-4-1-0-0-0'
        assert call.args[4] == 3
        assert call.args[5] is deps['job_repo']

    def test_tracks_running_window_for_tab_pill(self, mocker):
        '''
        Before the subprocess persists any rows the running window won't
        appear in ``aggregate_windows``. The panel must track it locally
        so :func:`auto_select_window` can return it and the running pill
        renders on the right tab.

        Captures ``_running_window`` inside the ``mutex.start`` side_effect
        — that's the moment between assignment and the ``finally`` clear,
        which is when the running pill needs to be visible.
        '''
        panel, deps = _make_panel(mocker)
        captured: dict[str, WindowKey | None] = {}

        def capture(phase, coro):
            captured['running'] = panel._running_window
            captured['selected'] = panel._selected_window
            return _completed_task()
        deps['phase_mutex'].start.side_effect = capture
        mocker.patch.object(oos_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        expected_key = derive_window_key('2025-1-1-0-0-0', '2025-4-1-0-0-0')
        assert captured['running'] == expected_key
        assert captured['selected'] == expected_key
        # And cleared again once the task completes.
        assert panel._running_window is None

    def test_clears_running_window_after_task_completes(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].start.side_effect = lambda phase, coro: _completed_task()
        mocker.patch.object(oos_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        assert panel._running_window is None

    def test_rolls_back_running_state_when_mutex_start_raises(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].start.side_effect = RuntimeError(
            "Cannot start 'oos': 'is' is already running"
        )
        notify = mocker.patch.object(oos_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        assert deps['set_running'].call_args_list[-1].args == (None,)
        assert panel._running_window is None
        notify.assert_called_once()
        assert notify.call_args.kwargs['type'] == 'negative'
        assert 'is already running' in notify.call_args.args[0]

    def test_notifies_warning_when_task_cancelled(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].start.side_effect = (
            lambda phase, coro: _failing_task(asyncio.CancelledError())
        )
        notify = mocker.patch.object(oos_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        notify.assert_called_once()
        assert notify.call_args.kwargs['type'] == 'warning'
        assert 'cancelled' in notify.call_args.args[0]

    def test_notifies_negative_when_task_raises(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].start.side_effect = (
            lambda phase, coro: _failing_task(RuntimeError('subprocess died'))
        )
        notify = mocker.patch.object(oos_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        notify.assert_called_once()
        assert notify.call_args.kwargs['type'] == 'negative'
        assert 'subprocess died' in notify.call_args.args[0]

    def test_does_not_notify_on_clean_completion(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].start.side_effect = lambda phase, coro: _completed_task()
        notify = mocker.patch.object(oos_panel_module.ui, 'notify')

        asyncio.run(panel._on_start())

        notify.assert_not_called()


@pytest.mark.ui
@pytest.mark.walk_forward_oos_panel
class TestOnStop:
    def test_returns_silently_when_not_active(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].is_active.return_value = False
        confirm = mocker.patch.object(oos_panel_module, 'confirm_dialog')

        asyncio.run(panel._on_stop())

        confirm.assert_not_called()
        deps['phase_mutex'].cancel.assert_not_called()

    def test_cancels_when_user_confirms(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].is_active.return_value = True

        async def fake_confirm(**kwargs):
            return True
        mocker.patch.object(oos_panel_module, 'confirm_dialog', side_effect=fake_confirm)

        asyncio.run(panel._on_stop())

        deps['phase_mutex'].cancel.assert_called_once()

    def test_does_not_cancel_when_user_declines(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].is_active.return_value = True

        async def fake_confirm(**kwargs):
            return False
        mocker.patch.object(oos_panel_module, 'confirm_dialog', side_effect=fake_confirm)

        asyncio.run(panel._on_stop())

        deps['phase_mutex'].cancel.assert_not_called()


@pytest.mark.ui
@pytest.mark.walk_forward_oos_panel
class TestOnProgress:
    def test_progress_increments_count(self, mocker):
        panel, _ = _make_panel(mocker)
        panel._progress_total = 10

        panel._on_progress(StreamEvent(event='PROGRESS', payload={'trial': 1}))
        panel._on_progress(StreamEvent(event='PROGRESS', payload={'trial': 2}))

        assert panel._progress_count == 2

    def test_done_jumps_count_to_total(self, mocker):
        '''
        DONE may arrive without a final PROGRESS for the last trial
        (subprocess emits DONE after the loop). Snap to total so the
        label reads ``X of X`` rather than stalling one short.
        '''
        panel, _ = _make_panel(mocker)
        panel._progress_total = 5
        panel._progress_count = 3

        panel._on_progress(StreamEvent(event='DONE', payload={'trials': 5}))

        assert panel._progress_count == 5

    def test_unknown_event_is_ignored(self, mocker):
        panel, _ = _make_panel(mocker)
        panel._progress_total = 10
        panel._progress_count = 3

        panel._on_progress(StreamEvent(event='BOGUS', payload={}))

        assert panel._progress_count == 3


@pytest.mark.ui
@pytest.mark.walk_forward_oos_panel
class TestEffectiveRunningWindow:
    '''
    The page's phase-done listener re-renders this panel synchronously
    inside ``mutex._on_task_done``, which fires before ``_on_start``'s
    ``finally`` clears ``_running_window``. Gating on the mutex keeps a
    stale LIVE pill off the just-finished tab and off another study's
    tabs after a mid-run study switch.
    '''

    def test_returns_running_window_while_oos_active(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].is_active.return_value = True
        panel._running_window = (100.0, 200.0)

        assert panel._effective_running_window() == (100.0, 200.0)
        deps['phase_mutex'].is_active.assert_called_with('oos')

    def test_returns_none_when_oos_no_longer_active(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].is_active.return_value = False
        panel._running_window = (100.0, 200.0)

        assert panel._effective_running_window() is None

    def test_returns_none_when_no_running_window_set(self, mocker):
        panel, deps = _make_panel(mocker)
        deps['phase_mutex'].is_active.return_value = True
        panel._running_window = None

        assert panel._effective_running_window() is None


@pytest.mark.ui
@pytest.mark.walk_forward_oos_panel
class TestParamsCache:
    def test_copy_uses_cached_params_without_lazy_fetch(self, mocker):
        panel, deps = _make_panel(mocker)
        panel._params_cache = {7: {'sma_window': 12}}
        get_trial_params = mocker.patch.object(
            oos_panel_module, 'get_trial_params'
        )
        run_javascript = mocker.patch.object(oos_panel_module.ui, 'run_javascript')
        mocker.patch.object(oos_panel_module.ui, 'notify')

        from ui.models.walk_forward import TrialVerdict, TrialWithOos
        trial = TrialWithOos(
            trial_number=7, is_value=1.0, oos_score=None,
            delta=None, verdict=TrialVerdict.PENDING, params={},
        )
        asyncio.run(panel._on_copy_params(trial))

        get_trial_params.assert_not_called()
        run_javascript.assert_called_once()

    def test_copy_falls_back_to_lazy_fetch_on_cache_miss(self, mocker):
        '''
        Per WF7 prefetch failure → lazy fetch on click. The button stays
        visible regardless.
        '''
        panel, deps = _make_panel(mocker)
        panel._params_cache = {}  # prefetch failed
        get_trial_params = mocker.patch.object(
            oos_panel_module, 'get_trial_params',
            return_value={'sma_window': 9},
        )
        run_javascript = mocker.patch.object(oos_panel_module.ui, 'run_javascript')
        mocker.patch.object(oos_panel_module.ui, 'notify')

        from ui.models.walk_forward import TrialVerdict, TrialWithOos
        trial = TrialWithOos(
            trial_number=42, is_value=1.0, oos_score=None,
            delta=None, verdict=TrialVerdict.PENDING, params={},
        )
        asyncio.run(panel._on_copy_params(trial))

        get_trial_params.assert_called_once_with(deps['selected'].name, 42)
        run_javascript.assert_called_once()

    def test_copy_notifies_when_lazy_fetch_fails(self, mocker):
        panel, _ = _make_panel(mocker)
        panel._params_cache = {}
        mocker.patch.object(
            oos_panel_module, 'get_trial_params',
            side_effect=RuntimeError('storage offline'),
        )
        run_javascript = mocker.patch.object(oos_panel_module.ui, 'run_javascript')
        notify = mocker.patch.object(oos_panel_module.ui, 'notify')

        from ui.models.walk_forward import TrialVerdict, TrialWithOos
        trial = TrialWithOos(
            trial_number=1, is_value=1.0, oos_score=None,
            delta=None, verdict=TrialVerdict.PENDING, params={},
        )
        asyncio.run(panel._on_copy_params(trial))

        run_javascript.assert_not_called()
        notify.assert_called_once()
        assert notify.call_args.kwargs['type'] == 'negative'

    def test_prefetch_populates_cache_from_bulk_fetch(self, mocker):
        '''
        The panel asks the service for params in one pass, keyed by trial
        number. Subsequent copy clicks then hit the cache rather than
        re-querying Optuna.
        '''
        panel, _ = _make_panel(mocker)
        from ui.models.walk_forward import TrialVerdict, TrialWithOos
        panel._trials = [
            TrialWithOos(
                trial_number=1, is_value=1.0, oos_score=None,
                delta=None, verdict=TrialVerdict.PENDING, params={},
            ),
            TrialWithOos(
                trial_number=2, is_value=0.9, oos_score=None,
                delta=None, verdict=TrialVerdict.PENDING, params={},
            ),
        ]
        bulk = mocker.patch.object(
            oos_panel_module, 'get_trial_params_bulk',
            return_value={1: {'sma': 5}, 2: {'sma': 10}},
        )

        panel._refresh_params_cache('study')

        assert panel._params_cache == {1: {'sma': 5}, 2: {'sma': 10}}
        call = bulk.call_args
        assert call.args[0] == 'study'
        assert sorted(call.args[1]) == [1, 2]

    def test_prefetch_failure_falls_back_to_empty_cache(self, mocker):
        '''
        If the bulk fetch raises (e.g. Optuna storage offline), the cache
        is cleared so every copy click falls back to the lazy lookup
        rather than wedging on a stale entry.
        '''
        panel, _ = _make_panel(mocker)
        from ui.models.walk_forward import TrialVerdict, TrialWithOos
        panel._trials = [
            TrialWithOos(
                trial_number=1, is_value=1.0, oos_score=None,
                delta=None, verdict=TrialVerdict.PENDING, params={},
            ),
        ]
        mocker.patch.object(
            oos_panel_module, 'get_trial_params_bulk',
            side_effect=RuntimeError('storage offline'),
        )

        panel._refresh_params_cache('study')

        assert panel._params_cache == {}

    def test_prefetch_with_no_trials_is_a_no_op(self, mocker):
        panel, _ = _make_panel(mocker)
        panel._trials = []
        bulk = mocker.patch.object(oos_panel_module, 'get_trial_params_bulk')

        panel._refresh_params_cache('study')

        assert panel._params_cache == {}
        bulk.assert_not_called()


@pytest.mark.ui
@pytest.mark.walk_forward_oos_panel
class TestOnUseAsTemplate:
    '''
    Re-evaluating an existing window after extending IS is the bread-and-
    butter walk-forward flow. The template button is the explicit
    affordance for it — populates the sidebar but does not run.
    '''

    def test_populates_start_and_end_inputs(self, mocker):
        panel, _ = _make_panel(
            mocker,
            start_value='2099-1-1-0-0-0',
            end_value='2099-1-2-0-0-0',
        )
        key = derive_window_key('2025-1-1-0-0-0', '2025-4-1-0-0-0')

        panel._on_use_as_template(key)

        assert panel._start_input.value == '2025-1-1-0-0-0'
        assert panel._end_input.value == '2025-4-1-0-0-0'

    def test_leaves_top_n_and_workers_untouched(self, mocker):
        '''
        Per design, Top N and Workers are independent of the window —
        the user often wants to re-run with the same trial budget on a
        different window, or vice versa.
        '''
        panel, _ = _make_panel(mocker, top_n_value='25', workers_value='4')
        key = derive_window_key('2025-1-1-0-0-0', '2025-4-1-0-0-0')

        panel._on_use_as_template(key)

        assert panel._top_n_input.value == '25'
        assert panel._workers_input.value == '4'

    def test_no_op_when_inputs_not_mounted(self, mocker):
        '''
        Defensive: ``_render_tabs`` already hides the button when OOS is
        running (inputs unmounted), but a stale callback shouldn't
        AttributeError if it slips through.
        '''
        panel, _ = _make_panel(mocker)
        panel._start_input = None
        panel._end_input = None
        key = derive_window_key('2025-1-1-0-0-0', '2025-4-1-0-0-0')

        panel._on_use_as_template(key)  # must not raise
