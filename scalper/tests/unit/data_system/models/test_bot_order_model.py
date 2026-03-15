import dataclasses
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from data_system.models.bot_order_model import BotOrder, OrderStatus, Side


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.bot_order_model
class TestBotOrder:
    @pytest.fixture
    def sample_order(self) -> BotOrder:
        ''' Fixture providing a sample BotOrder instance with only required fields set.'''
        return BotOrder(
            bot_id='btc_1m_001',
            run_id=uuid4(),
            exchange_order_id='OFLMR7-XXXXX-XXXXXX',
            side=Side.BUY,
        )

    def test_creates_bot_order_with_required_fields(self, sample_order: BotOrder):
        assert sample_order.bot_id == 'btc_1m_001'
        assert sample_order.exchange_order_id == 'OFLMR7-XXXXX-XXXXXX'
        assert sample_order.side == Side.BUY
        assert isinstance(sample_order.run_id, UUID)

    def test_id_is_auto_generated_uuid(self, sample_order: BotOrder):
        assert sample_order.id is not None
        assert isinstance(sample_order.id, UUID)

    def test_two_orders_have_different_ids(self):
        # Given
        run_id = uuid4()

        # When
        order1 = BotOrder(
            bot_id='btc_1m_001',
            run_id=run_id,
            exchange_order_id='TX1',
            side=Side.BUY
        )
        order2 = BotOrder(
            bot_id='btc_1m_001',
            run_id=run_id,
            exchange_order_id='TX2',
            side=Side.BUY
        )

        # Then
        assert order1.id != order2.id

    def test_id_can_be_set_explicitly(self, sample_order: BotOrder):
        # Given
        custom_id = uuid4()

        # When
        order = dataclasses.replace(sample_order, id=custom_id)

        # Then
        assert order.id == custom_id

    def test_status_defaults_to_placed(self, sample_order: BotOrder):
        # When / Then
        assert sample_order.status == OrderStatus.PLACED

    def test_placed_at_defaults_to_current_utc_time(self):
        # Given
        before = datetime.now(timezone.utc)

        # When
        order = BotOrder(
            bot_id='btc_1m_001',
            run_id=uuid4(),
            exchange_order_id='OFLMR7-XXXXX-XXXXXX',
            side=Side.BUY,
        )
        after = datetime.now(timezone.utc)

        # Then
        assert isinstance(order.placed_at, datetime)
        assert order.placed_at.tzinfo is not None
        assert before <= order.placed_at <= after

    def test_fill_fields_default_to_none(self, sample_order: BotOrder):
        assert sample_order.filled_at is None
        assert sample_order.price is None
        assert sample_order.volume is None
        assert sample_order.fee is None

    def test_tick_id_defaults_to_none(self, sample_order: BotOrder):
        assert sample_order.tick_id is None

    def test_order_with_sell_side(self, sample_order: BotOrder):
        order = dataclasses.replace(sample_order, side=Side.SELL)
        assert order.side == Side.SELL

    def test_bot_order_is_frozen(self, sample_order: BotOrder):
        with pytest.raises(AttributeError):
            sample_order.price = Decimal('60000.00')

    def test_replace_creates_filled_copy(self, sample_order: BotOrder):
        # Given
        filled_at = datetime.now(timezone.utc)

        # When
        filled = dataclasses.replace(
            sample_order,
            status=OrderStatus.FILLED,
            price=Decimal('50000.00'),
            volume=Decimal('0.001'),
            fee=Decimal('0.50'),
            filled_at=filled_at,
        )

        # Then
        assert filled.status == OrderStatus.FILLED
        assert filled.price == Decimal('50000.00')
        assert filled.volume == Decimal('0.001')
        assert filled.fee == Decimal('0.50')
        assert filled.filled_at == filled_at
        assert filled.exchange_order_id == sample_order.exchange_order_id
        assert filled.id == sample_order.id


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


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.bot_order_model
class TestOrderStatus:
    def test_placed_value(self):
        assert OrderStatus.PLACED.value == 'placed'

    def test_filled_value(self):
        assert OrderStatus.FILLED.value == 'filled'

    def test_failed_value(self):
        assert OrderStatus.FAILED.value == 'failed'

    def test_is_string_enum(self):
        assert isinstance(OrderStatus.PLACED, str)
        assert OrderStatus.PLACED == 'placed'
