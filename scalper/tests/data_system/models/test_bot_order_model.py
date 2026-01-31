from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from data_system.models.bot_order_model import BotOrder, Side


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.bot_order_model
class TestBotOrder:
    @pytest.fixture
    def sample_order_data(self):
        return {
            'bot_id': 'btc_1m_001',
            'run_id': uuid4(),
            'tick_id': 1,
            'side': Side.BUY,
            'price': Decimal('50000.00'),
            'volume': Decimal('0.001'),
            'fee': Decimal('0.50'),
            'executed_at': datetime.now(timezone.utc)
        }

    def test_creates_bot_order_with_required_fields(self, sample_order_data):
        # When
        order = BotOrder(**sample_order_data)

        # Then
        assert order.bot_id == sample_order_data['bot_id']
        assert order.run_id == sample_order_data['run_id']
        assert order.tick_id == sample_order_data['tick_id']
        assert order.side == Side.BUY
        assert order.price == sample_order_data['price']
        assert order.volume == sample_order_data['volume']
        assert order.fee == sample_order_data['fee']
        assert order.executed_at == sample_order_data['executed_at']

    def test_id_is_auto_generated_uuid(self, sample_order_data):
        # When
        order = BotOrder(**sample_order_data)

        # Then
        assert order.id is not None
        assert isinstance(order.id, UUID)

    def test_id_can_be_set_explicitly(self, sample_order_data):
        # Given
        custom_id = uuid4()

        # When
        order = BotOrder(**sample_order_data, id=custom_id)

        # Then
        assert order.id == custom_id

    def test_two_orders_have_different_ids(self, sample_order_data):
        # When
        order1 = BotOrder(**sample_order_data)
        order2 = BotOrder(**sample_order_data)

        # Then
        assert order1.id != order2.id

    def test_order_with_sell_side(self, sample_order_data):
        # Given
        sample_order_data['side'] = Side.SELL

        # When
        order = BotOrder(**sample_order_data)

        # Then
        assert order.side == Side.SELL

    def test_bot_order_is_frozen(self, sample_order_data):
        # Given
        order = BotOrder(**sample_order_data)

        # When / Then
        with pytest.raises(AttributeError):
            order.price = Decimal('60000.00')


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.bot_order_model
class TestSide:
    def test_side_buy_value(self):
        assert Side.BUY.value == 'buy'

    def test_side_sell_value(self):
        assert Side.SELL.value == 'sell'

    def test_side_is_string_enum(self):
        assert isinstance(Side.BUY, str)
        assert Side.BUY == 'buy'
