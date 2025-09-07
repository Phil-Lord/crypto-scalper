from datetime import datetime, timezone


def parse_datetime(datetime_string: str):
    '''
    Converts a datetime in the string format 'YYYY-MM-DD-hh-mm-ss' to a list of integers.

    E.g. '2025-1-28-23-59-59' -> [2025, 1, 28, 23, 59, 59].
    '''
    return [int(i) for i in datetime_string.split('-')]


def get_nano_timestamp(year: int, month: int = 1, day: int = 1, hour: int = 0, minute: int = 0, second: int = 0) -> int:
    '''
    The Kraken API Trades endpoint takes either second or nanosecond timestamps, and returns
    timestamps in seconds. However, the `last` field, which we use for iterative fetching, is
    returned in nanoseconds, e.g. 1727251626987654321.
    '''
    return int(datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc).timestamp() * 10**9)


def get_second_timestamp(year: int, month: int = 1, day: int = 1, hour: int = 0, minute: int = 0, second: int = 0) -> float:
    '''
    The Kraken API Trades endpoint returns timestamps in seconds (with the fractional part in
    microseconds), e.g. 1738022410.0468764.

    This is the format in which timestamps are saved in the Trades database table.
    '''
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc).timestamp()
