from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from data_system.models.bot_tick_model import BotTick, Signal


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.bot_tick_model
class TestBotTick:
    @pytest.fixture
    def sample_tick_data(self):
        return {
            'bot_id': 'btc_1m_001',
            'run_id': uuid4(),
            'timestamp': datetime.now(timezone.utc),
            'price': Decimal('50000.00'),
            'signal': Signal.HOLD,
            'balance_base': Decimal('0.001'),
            'balance_quote': Decimal('100.00')
        }

    def test_creates_bot_tick_with_required_fields(self, sample_tick_data):
        # When
        tick = BotTick(**sample_tick_data)

        # Then
        assert tick.bot_id == sample_tick_data['bot_id']
        assert tick.run_id == sample_tick_data['run_id']
        assert tick.timestamp == sample_tick_data['timestamp']
        assert tick.price == sample_tick_data['price']
        assert tick.signal == Signal.HOLD
        assert tick.balance_base == sample_tick_data['balance_base']
        assert tick.balance_quote == sample_tick_data['balance_quote']

    def test_error_defaults_to_none(self, sample_tick_data):
        # When
        tick = BotTick(**sample_tick_data)

        # Then
        assert tick.error is None

    def test_id_defaults_to_none(self, sample_tick_data):
        # When
        tick = BotTick(**sample_tick_data)

        # Then
        assert tick.id is None

    def test_error_can_be_set(self, sample_tick_data):
        # Given
        error_msg = 'Shaboola!'

        # When
        tick = BotTick(**sample_tick_data, error=error_msg)

        # Then
        assert tick.error == error_msg

    def test_id_can_be_set(self, sample_tick_data):
        # When
        tick = BotTick(**sample_tick_data, id=42)

        # Then
        assert tick.id == 42

    def test_tick_with_buy_signal(self, sample_tick_data):
        # Given
        sample_tick_data['signal'] = Signal.BUY

        # When
        tick = BotTick(**sample_tick_data)

        # Then
        assert tick.signal == Signal.BUY

    def test_tick_with_sell_signal(self, sample_tick_data):
        # Given
        sample_tick_data['signal'] = Signal.SELL

        # When
        tick = BotTick(**sample_tick_data)

        # Then
        assert tick.signal == Signal.SELL

    def test_bot_tick_is_frozen(self, sample_tick_data):
        # Given
        tick = BotTick(**sample_tick_data)

        # When / Then
        with pytest.raises(AttributeError):
            tick.price = Decimal('60000.00')


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.bot_tick_model
class TestSignal:
    def test_signal_buy_value(self):
        assert Signal.BUY.value == 'buy'

    def test_signal_hold_value(self):
        assert Signal.HOLD.value == 'hold'

    def test_signal_sell_value(self):
        assert Signal.SELL.value == 'sell'

    def test_signal_is_string_enum(self):
        assert isinstance(Signal.BUY, str)
        assert Signal.BUY == 'buy'
        assert isinstance(Signal.HOLD, str)
        assert Signal.HOLD == 'hold'
        assert isinstance(Signal.SELL, str)
        assert Signal.SELL == 'sell'
