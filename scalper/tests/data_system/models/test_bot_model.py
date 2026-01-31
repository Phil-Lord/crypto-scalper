from datetime import datetime, timezone

import pytest

from data_system.models.bot_model import Bot


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.bot_model
class TestBot:
    @pytest.fixture
    def sample_bot_data(self):
        return {
            'id': 'btc_1m_001',
            'pair': 'XXBTZGBP',
            'strategy_name': 'TestStrategy',
            'strategy_version': 'v1.0.0',
            'interval': 1,
            'parameters': {'param1': 10, 'param2': 20}
        }

    def test_creates_bot_with_required_fields(self, sample_bot_data):
        # When
        bot = Bot(**sample_bot_data)

        # Then
        assert bot.id == sample_bot_data['id']
        assert bot.pair == sample_bot_data['pair']
        assert bot.strategy_name == sample_bot_data['strategy_name']
        assert bot.strategy_version == sample_bot_data['strategy_version']
        assert bot.interval == sample_bot_data['interval']
        assert bot.parameters == sample_bot_data['parameters']

    def test_created_at_defaults_to_current_time(self, sample_bot_data):
        # Given
        before = datetime.now(timezone.utc)

        # When
        bot = Bot(**sample_bot_data)

        # Then
        after = datetime.now(timezone.utc)
        assert before <= bot.created_at <= after

    def test_created_at_can_be_set_explicitly(self, sample_bot_data):
        # Given
        custom_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        # When
        bot = Bot(**sample_bot_data, created_at=custom_time)

        # Then
        assert bot.created_at == custom_time

    def test_bot_is_frozen(self, sample_bot_data):
        # Given
        bot = Bot(**sample_bot_data)

        # When / Then
        with pytest.raises(AttributeError):
            bot.id = 'new_id'

    def test_bot_with_empty_parameters(self, sample_bot_data):
        # Given
        sample_bot_data['parameters'] = {}

        # When
        bot = Bot(**sample_bot_data)

        # Then
        assert bot.parameters == {}

    def test_bot_with_complex_parameters(self, sample_bot_data):
        # Given
        sample_bot_data['parameters'] = {
            'ema_short': 12,
            'ema_long': 26,
            'nested': {'threshold': 0.5}
        }

        # When
        bot = Bot(**sample_bot_data)

        # Then
        assert bot.parameters['ema_short'] == 12
        assert bot.parameters['nested']['threshold'] == 0.5
