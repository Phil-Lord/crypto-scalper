import pytest

from data_system import OosWindowAggregate
from ui.pages.walk_forward.components.window_tabs import (
    auto_select_window,
    format_window_dates,
)
from ui.pages.walk_forward.components.oos_panel import derive_window_key


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


@pytest.mark.ui
@pytest.mark.walk_forward_window_tabs
class TestFormatWindowDates:
    def test_round_trips_through_derive_window_key(self):
        '''
        ``format_window_dates`` and ``derive_window_key`` must be inverses
        — when the "use as template" button populates the sidebar form,
        the user's next EVALUATE click must resolve to the original
        ``(start_ts, end_ts)`` so trials line up with the existing window.
        '''
        original = ('2025-1-1-0-0-0', '2025-4-1-0-0-0')
        key = derive_window_key(*original)

        formatted = format_window_dates(key)

        assert formatted == original
        assert derive_window_key(*formatted) == key

    def test_emits_unpadded_components(self):
        '''
        The sidebar form's ``parse_datetime`` accepts unpadded numbers
        (``'2025-1-1-0-0-0'``, not ``'2025-01-01-00-00-00'``). Match.
        '''
        key = derive_window_key('2025-1-1-0-0-0', '2025-12-31-23-59-59')
        start, end = format_window_dates(key)
        assert start == '2025-1-1-0-0-0'
        assert end == '2025-12-31-23-59-59'
