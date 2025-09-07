import pytest

from utils import parse_datetime, get_nano_timestamp, get_second_timestamp


@pytest.mark.timestamp_conversion
class TestTimestampConversion:
    # --- parse_datetime --- #
    @pytest.mark.parse_datetime
    def test_parse_datetime(self):
        assert parse_datetime('2025-1-28-23-59-59') == [2025, 1, 28, 23, 59, 59]
        assert parse_datetime('2025-1-28-23-59') == [2025, 1, 28, 23, 59]
        assert parse_datetime('2025-1-28-23') == [2025, 1, 28, 23]
        assert parse_datetime('2025-1-28') == [2025, 1, 28]
        assert parse_datetime('2025-1') == [2025, 1]
        assert parse_datetime('2025') == [2025]

    # --- get_nano_timestamp --- #
    @pytest.mark.get_nano_timestamp
    def test_get_nano_timestamp_precision(self):
        ts = get_nano_timestamp(2025)
        assert isinstance(ts, int)
        assert len(str(ts)) == 19  # Nanosecond precision

    @pytest.mark.get_nano_timestamp
    def test_get_nano_timestamp_specific_date(self):
        assert get_nano_timestamp(2024, 9, 25, 12, 34, 56) == 1727267696000000000

    @pytest.mark.get_nano_timestamp
    def test_get_nano_timestamp_day_difference(self):
        day_one_ts = get_nano_timestamp(2018, 7, 6, 5, 43, 21)
        day_two_ts = get_nano_timestamp(2018, 7, 7, 5, 43, 21)
        assert day_two_ts - day_one_ts == 86400000000000  # One day in nanoseconds

    # --- get_second_timestamp --- #
    @pytest.mark.get_second_timestamp
    def test_get_second_timestamp_precision(self):
        ts = get_second_timestamp(2024, 9, 25, 12, 34, 56)
        assert isinstance(ts, float)
        assert ts > 0
        assert len(str(int(ts))) == 10  # Second precision

    @pytest.mark.get_second_timestamp
    def test_get_second_timestamp_specific_date(self):
        assert get_second_timestamp(2024, 9, 25, 12, 34, 56) == 1727267696.0

    @pytest.mark.get_second_timestamp
    def test_get_second_timestamp_day_difference(self):
        july_13_ts = get_second_timestamp(2024, 7, 13)
        july_14_ts = get_second_timestamp(2024, 7, 14)
        assert july_14_ts - july_13_ts == 86400  # One day in seconds
