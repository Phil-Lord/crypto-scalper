import pytest

from data_system import OosWindowAggregate
from ui.pages.walk_forward.components.window_tabs import auto_select_window


def _window(start: float, end: float) -> OosWindowAggregate:
    return OosWindowAggregate(
        start=start,
        end=end,
        best_oos=0.5,
        generalised_count=0,
        overfit_count=0,
    )


@pytest.mark.ui
@pytest.mark.walk_forward_window_tabs
class TestAutoSelectWindow:
    def test_returns_running_window_when_set(self):
        '''
        The in-flight evaluation always wins, so the user sees scores for
        the window being evaluated even when older windows exist.
        '''
        windows = [_window(100.0, 200.0), _window(300.0, 400.0)]
        running = (500.0, 600.0)

        assert auto_select_window(windows, running) == running

    def test_returns_running_window_even_when_not_in_aggregates(self):
        '''
        Before any trial in the running window has been persisted,
        ``aggregate_windows`` will not surface it. The selector must
        still return the running tuple so the panel can render it.
        '''
        windows: list[OosWindowAggregate] = []
        running = (500.0, 600.0)

        assert auto_select_window(windows, running) == running

    def test_returns_last_window_when_no_run_in_flight(self):
        '''
        ``aggregate_windows`` orders rows ascending by start_timestamp;
        'most recently created' is the last row.
        '''
        windows = [_window(100.0, 200.0), _window(300.0, 400.0)]

        assert auto_select_window(windows, None) == (300.0, 400.0)

    def test_returns_none_when_idle_and_no_windows(self):
        assert auto_select_window([], None) is None

    def test_running_wins_over_idle_selection(self):
        '''
        Even with existing windows present, a running evaluation must
        steal the selection so the trials table tracks live progress
        rather than a historic window.
        '''
        windows = [_window(100.0, 200.0), _window(300.0, 400.0)]
        running = (500.0, 600.0)

        assert auto_select_window(windows, running) == running
