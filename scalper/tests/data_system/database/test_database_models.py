from data_system.database.models import Trade


def test_trade_model_fields():
    trade = Trade(
        trade_id=1,
        pair='BTCGBP',
        price=100.0,
        volume=1.0,
        timestamp=1234567890.0,
        side='b',
        order_type='l'
    )
    assert trade.trade_id == 1
    assert trade.pair == 'BTCGBP'
    assert trade.price == 100.0
    assert trade.volume == 1.0
    assert trade.timestamp == 1234567890.0
    assert trade.side == 'b'
    assert trade.order_type == 'l'
