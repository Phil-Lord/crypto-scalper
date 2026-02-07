import pytest

from data_system.models.trade_model import Trade


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.trade_model
class TestTrade:
    @pytest.fixture
    def sample_trade_data(self):
        return {
            'trade_id': 123456789,
            'pair': 'XXBTZGBP',
            'price': 50000.0,
            'volume': 0.001,
            'timestamp': 1704067200.123,
            'side': 'b',
            'order_type': 'm'
        }

    def test_creates_trade_with_all_fields(self, sample_trade_data):
        # When
        trade = Trade(**sample_trade_data)

        # Then
        assert trade.trade_id == sample_trade_data['trade_id']
        assert trade.pair == sample_trade_data['pair']
        assert trade.price == sample_trade_data['price']
        assert trade.volume == sample_trade_data['volume']
        assert trade.timestamp == sample_trade_data['timestamp']
        assert trade.side == sample_trade_data['side']
        assert trade.order_type == sample_trade_data['order_type']

    def test_creates_trade_with_sell_side(self, sample_trade_data):
        # Given
        sample_trade_data['side'] = 's'

        # When
        trade = Trade(**sample_trade_data)

        # Then
        assert trade.side == 's'

    def test_creates_trade_with_limit_order_type(self, sample_trade_data):
        # Given
        sample_trade_data['order_type'] = 'l'

        # When
        trade = Trade(**sample_trade_data)

        # Then
        assert trade.order_type == 'l'

    def test_trade_with_high_precision_timestamp(self, sample_trade_data):
        # Given
        sample_trade_data['timestamp'] = 1704067200.999999

        # When
        trade = Trade(**sample_trade_data)

        # Then
        assert trade.timestamp == 1704067200.999999

    def test_trade_with_different_pair(self, sample_trade_data):
        # Given
        sample_trade_data['pair'] = 'XETHZUSD'

        # When
        trade = Trade(**sample_trade_data)

        # Then
        assert trade.pair == 'XETHZUSD'

    def test_trade_is_frozen(self, sample_trade_data):
        # Given
        trade = Trade(**sample_trade_data)

        # When / Then
        with pytest.raises(AttributeError):
            trade.price = 60000.0

    def test_trade_with_large_volume(self, sample_trade_data):
        # Given
        sample_trade_data['volume'] = 100.12345678

        # When
        trade = Trade(**sample_trade_data)

        # Then
        assert trade.volume == 100.12345678

    def test_trade_with_large_trade_id(self, sample_trade_data):
        # Given
        sample_trade_data['trade_id'] = 9999999999999

        # When
        trade = Trade(**sample_trade_data)

        # Then
        assert trade.trade_id == 9999999999999
