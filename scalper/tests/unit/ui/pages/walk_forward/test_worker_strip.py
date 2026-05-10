import pytest

from ui.pages.walk_forward.components.worker_strip import WorkerStrip


@pytest.mark.ui
@pytest.mark.walk_forward_worker_strip
class TestWorkerStrip:
    def test_mark_pending_as_rejects_unknown_status(self):
        '''
        The guard fires before the strip touches any tile or NiceGUI element,
        so we can call it without an instance — instantiating the strip
        requires a NiceGUI client context.
        '''
        with pytest.raises(ValueError, match='Unknown WorkerStrip status'):
            WorkerStrip.mark_pending_as(
                WorkerStrip.__new__(WorkerStrip),
                'bogus',  # type: ignore[arg-type]
            )

    def test_error_message_lists_supported_statuses(self):
        with pytest.raises(ValueError) as exc:
            WorkerStrip.mark_pending_as(
                WorkerStrip.__new__(WorkerStrip),
                'nope',  # type: ignore[arg-type]
            )

        message = str(exc.value)
        for status in ('pending', 'running', 'done', 'error', 'cancelled'):
            assert status in message
