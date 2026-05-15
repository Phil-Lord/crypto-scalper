import pytest

from ui.pages.walk_forward.components.study_rail_row import StudyRailRow
from utils import StudyDirection, StudySummary


def _summary() -> StudySummary:
    return StudySummary(
        name='SmaStrategy_XXBTZGBP_20240101-20240601',
        pair='XXBTZGBP',
        strategy='SmaStrategy',
        trial_count=5,
        best_is=1.23,
        direction=StudyDirection.MAXIMIZE,
    )


@pytest.mark.ui
@pytest.mark.walk_forward_study_rail_row
class TestStudyRailRow:
    def test_rejects_unknown_last_run_state(self):
        '''
        The guard fires before any NiceGUI element is created, so 'cancelled'
        / 'error' (pill vocabulary, not rail vocabulary) must be caught here
        rather than silently rendered.
        '''
        with pytest.raises(ValueError, match='Unknown StudyRailRow last_run_state'):
            StudyRailRow(
                _summary(),
                active=True,
                last_run_state='cancelled',
                on_click=lambda: None,
            )

    def test_error_message_names_supported_states(self):
        with pytest.raises(ValueError) as exc:
            StudyRailRow(
                _summary(),
                active=False,
                last_run_state='nope',
                on_click=lambda: None,
            )

        message = str(exc.value)
        assert 'running' in message
        assert 'idle' in message
