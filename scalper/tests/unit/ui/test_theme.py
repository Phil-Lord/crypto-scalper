import pytest

from ui.theme import SectionTitle, StatusPill


@pytest.mark.ui
@pytest.mark.theme_status_pill
class TestStatusPill:
    def test_rejects_unknown_status(self):
        with pytest.raises(ValueError, match='Unknown StatusPill status'):
            StatusPill('not-a-status')

    def test_error_message_lists_supported_statuses(self):
        '''
        The guard error must enumerate the supported statuses so a typo at a
        call site is fixable from the traceback alone.
        '''
        with pytest.raises(ValueError) as exc:
            StatusPill('idle')  # 'idle' is rail-row vocabulary, not pill vocabulary.

        message = str(exc.value)
        for status in ('running', 'pending', 'done', 'error', 'cancelled'):
            assert status in message


@pytest.mark.ui
@pytest.mark.theme_section_title
class TestSectionTitle:
    def test_renders_without_pill(self):
        '''
        Smoke test: SectionTitle has no return value to assert against, so we
        just verify it can be constructed without raising when no pill is
        supplied.
        '''
        SectionTitle('01', 'IN-SAMPLE')

    def test_forwards_pill_status_validation_to_status_pill(self):
        '''
        The pill tuple is unpacked and handed to ``StatusPill``, so an unknown
        status must surface the same guard error rather than rendering a
        miscoloured chip.
        '''
        with pytest.raises(ValueError, match='Unknown StatusPill status'):
            SectionTitle('01', 'IN-SAMPLE', pill=('not-a-status', None))
