from datetime import datetime, timezone
from uuid import UUID

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

    def test_id_is_auto_generated_uuid(self):
        # When
        bot_run = BotRun(bot_id='test_bot')

        # Then
        assert bot_run.id is not None
        assert isinstance(bot_run.id, UUID)

    def test_started_at_defaults_to_current_time(self):
        # Given
        before = datetime.now(timezone.utc)

        # When
        bot_run = BotRun(bot_id='test_bot')

        # Then
        after = datetime.now(timezone.utc)
        assert before <= bot_run.started_at <= after

    def test_completed_at_defaults_to_none(self):
        # When
        bot_run = BotRun(bot_id='test_bot')

        # Then
        assert bot_run.completed_at is None

    def test_completed_at_can_be_set(self):
        # Given
        completed = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)

        # When
        bot_run = BotRun(bot_id='test_bot', completed_at=completed)

        # Then
        assert bot_run.completed_at == completed

    def test_two_runs_have_different_ids(self):
        # When
        run1 = BotRun(bot_id='test_bot')
        run2 = BotRun(bot_id='test_bot')

        # Then
        assert run1.id != run2.id

    def test_bot_run_is_frozen(self):
        # Given
        bot_run = BotRun(bot_id='test_bot')

        # When / Then
        with pytest.raises(AttributeError):
            bot_run.bot_id = 'new_bot'
