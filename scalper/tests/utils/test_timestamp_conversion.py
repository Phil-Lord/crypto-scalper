from utils import parse_datetime, get_nano_timestamp, get_second_timestamp


def test_parse_datetime():
    dt = '2025-1-28-23-59-59'
    result = parse_datetime(dt)
    assert result == [2025, 1, 28, 23, 59, 59]


def test_get_nano_timestamp():
    ts = get_nano_timestamp(2025, 1, 1)
    assert isinstance(ts, int)
    assert len(str(ts)) >= 10


def test_get_second_timestamp():
    ts = get_second_timestamp(2025, 1, 1)
    assert isinstance(ts, float)
    assert ts > 0
