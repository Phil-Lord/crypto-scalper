from datetime import datetime

import pytest

from data_system.models.bot_model import Bot


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.bot_model
class TestBot:
    def test_creates_bot_with_required_fields(self):
        # Given
        bot_id = 'btc_1m_001'
        pair = 'XXBTZGBP'
        strategy_name = 'TestStrategy'
        strategy_version = 'v1.0.0'
        interval = 1
        parameters = {'param1': 10, 'param2': 20}

        # When
        bot = Bot(
            id=bot_id,
            pair=pair,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            interval=interval,
            parameters=parameters
        )

        # Then
        assert bot.id == bot_id
        assert bot.pair == pair
        assert bot.strategy_name == strategy_name
        assert bot.strategy_version == strategy_version
        assert bot.interval == interval
        assert bot.parameters == parameters
        assert isinstance(bot.created_at, datetime)
