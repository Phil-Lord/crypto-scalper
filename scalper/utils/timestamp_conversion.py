'''
Timestamp helpers, including converters for the Kraken Trades endpoint.

Kraken's `/0/public/Trades` endpoint mixes three different timestamp formats in a single
response. Keeping them straight is the source of most timestamp confusion in this codebase:

1. **`since` query parameter** — accepts EITHER seconds (10-digit int) OR nanoseconds
    (19-digit int). Kraken auto-detects by magnitude. Anything in between — milliseconds
    (13-digit) or microseconds (16-digit) — is silently misinterpreted as nanoseconds; the
    value reads as a moment in ~1970 and Kraken returns the earliest trades it has on file.
    Only ever pass seconds or nanoseconds. We use nanoseconds internally so the input format
    matches the `last` cursor (point 2).

2. **`result['last']` pagination cursor** — ALWAYS returned in nanoseconds (19-digit
    string), regardless of which format `since` used. We feed it back as the next `since`
    verbatim, so pagination loops are nanoseconds end-to-end.

3. **Per-trade timestamp at `result[pair][i][2]`** — returned in seconds with fractional
    microseconds, e.g. `1738022410.0468764`. This is what gets stored in the
    `trades.timestamp` column.

Two converters are exposed, one per output format:

- `get_nano_timestamp`   — for `since`/`until` bounds passed to the Kraken API.
- `get_second_timestamp` — for comparing against stored trade timestamps.
'''

from datetime import datetime, timezone


def parse_datetime(datetime_string: str) -> list[int]:
    '''
    Converts a datetime in the string format 'YYYY-MM-DD-hh-mm-ss' to a list of integers.

    E.g. '2025-1-28-23-59-59' -> [2025, 1, 28, 23, 59, 59].
    '''
    return [int(i) for i in datetime_string.split('-')]


def get_nano_timestamp(year: int, month: int = 1, day: int = 1, hour: int = 0, minute: int = 0, second: int = 0) -> int:
    '''
    Converts a UTC datetime to a nanosecond Unix timestamp.

    Use this when constructing `since`/`until` bounds for the Kraken Trades endpoint — see
    the module docstring for why nanoseconds are the safe internal format.
    '''
    return int(datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc).timestamp() * 10**9)


def get_second_timestamp(year: int, month: int = 1, day: int = 1, hour: int = 0, minute: int = 0, second: int = 0) -> float:
    '''
    Converts a UTC datetime to a fractional-second Unix timestamp.

    Matches the format of per-trade timestamps in the Kraken response and the
    `trades.timestamp` column.
    '''
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc).timestamp()
