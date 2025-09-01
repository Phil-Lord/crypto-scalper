from utils import parse_datetime, get_nano_timestamp, get_second_timestamp


def test_parse_datetime():
    assert parse_datetime('2025-1-28-23-59-59') == [2025, 1, 28, 23, 59, 59]
    assert parse_datetime('2025-1-28-23-59') == [2025, 1, 28, 23, 59]
    assert parse_datetime('2025-1-28-23') == [2025, 1, 28, 23]
    assert parse_datetime('2025-1-28') == [2025, 1, 28]
    assert parse_datetime('2025-1') == [2025, 1]
    assert parse_datetime('2025') == [2025]


def test_get_nano_timestamp_precision():
    ts = get_nano_timestamp(2025, 1, 1)
    assert isinstance(ts, int)
    assert len(str(ts)) == 19  # Nanosecond precision


def test_get_nano_timestamp_specific_date():
    assert get_nano_timestamp(2024, 9, 25, 12, 34, 56) == 1727264096000000000


def test_get_nano_timestamp_day_difference():
    july_13_ts = get_nano_timestamp(2024, 7, 13)
    july_14_ts = get_nano_timestamp(2024, 7, 14)
    assert july_14_ts - july_13_ts == 86400 * 1000000000  # One day in nanoseconds


def test_get_second_timestamp_precision():
    ts = get_second_timestamp(2024, 9, 25, 12, 34, 56)
    assert isinstance(ts, float)
    assert ts > 0
    assert len(str(int(ts))) == 10  # Second precision


def test_get_second_timestamp_specific_date():
    assert get_second_timestamp(2024, 9, 25, 12, 34, 56) == 1727264096.0


def test_get_second_timestamp_day_difference():
    july_13_ts = get_second_timestamp(2024, 7, 13)
    july_14_ts = get_second_timestamp(2024, 7, 14)
    assert july_14_ts - july_13_ts == 86400  # One day in seconds
