import pytest

from ui.theme import StatusPill


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
