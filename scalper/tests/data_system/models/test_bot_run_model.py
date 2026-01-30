from datetime import datetime

import pytest

from data_system.models.bot_run_model import BotRun


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.bot_run_model
class TestBotRun:
    def test_creates_bot_run_with_required_fields(self):
        # Given
        bot_id = 'btc_1m_001'

        # When
        bot_run = BotRun(bot_id=bot_id)

        # Then
        assert bot_run.bot_id == bot_id
        assert bot_run.id is not None
        assert isinstance(bot_run.started_at, datetime)
        assert bot_run.completed_at is None
