from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from data_system.models.bot_order_model import BotOrder, Side


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.bot_order_model
class TestBotOrder:
    def test_creates_bot_order_with_required_fields(self):
        # Given
        bot_id = 'btc_1m_001'
        run_id = uuid4()
        tick_id = 1
        side = Side.BUY
        price = Decimal('50000.00')
        volume = 0.001
        fee = Decimal('0.50')
        executed_at = datetime.now(timezone.utc)

        # When
        order = BotOrder(
            bot_id=bot_id,
            run_id=run_id,
            tick_id=tick_id,
            side=side,
            price=price,
            volume=volume,
            fee=fee,
            executed_at=executed_at
        )

        # Then
        assert order.bot_id == bot_id
        assert order.run_id == run_id
        assert order.tick_id == tick_id
        assert order.side == Side.BUY
        assert order.price == price
        assert order.volume == volume
        assert order.fee == fee
        assert order.executed_at == executed_at
        assert order.id is not None
