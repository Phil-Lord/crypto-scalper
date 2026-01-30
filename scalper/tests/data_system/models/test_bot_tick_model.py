from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from data_system.models.bot_tick_model import BotTick, Signal


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.bot_tick_model
class TestBotTick:
    def test_creates_bot_tick_with_required_fields(self):
        # Given
        bot_id = 'btc_1m_001'
        run_id = uuid4()
        timestamp = datetime.now(timezone.utc)
        price = Decimal('50000.00')
        signal = Signal.HOLD
        balance_base = Decimal('0.001')
        balance_quote = Decimal('100.00')

        # When
        tick = BotTick(
            bot_id=bot_id,
            run_id=run_id,
            timestamp=timestamp,
            price=price,
            signal=signal,
            balance_base=balance_base,
            balance_quote=balance_quote
        )

        # Then
        assert tick.bot_id == bot_id
        assert tick.run_id == run_id
        assert tick.timestamp == timestamp
        assert tick.price == price
        assert tick.signal == Signal.HOLD
        assert tick.balance_base == balance_base
        assert tick.balance_quote == balance_quote
        assert tick.error is None
        assert tick.id is None
