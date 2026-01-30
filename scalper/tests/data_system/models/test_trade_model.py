import pytest

from data_system.models.trade_model import Trade


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.trade_model
class TestTrade:
    def test_creates_trade_with_all_fields(self):
        # Given
        trade_id = 123456789
        pair = 'XXBTZGBP'
        price = 50000.0
        volume = 0.001
        timestamp = 1704067200.123
        side = 'b'
        order_type = 'm'

        # When
        trade = Trade(
            trade_id=trade_id,
            pair=pair,
            price=price,
            volume=volume,
            timestamp=timestamp,
            side=side,
            order_type=order_type
        )

        # Then
        assert trade.trade_id == trade_id
        assert trade.pair == pair
        assert trade.price == price
        assert trade.volume == volume
        assert trade.timestamp == timestamp
        assert trade.side == side
        assert trade.order_type == order_type
