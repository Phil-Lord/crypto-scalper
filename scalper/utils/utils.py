import datetime
import time


def parse_datetime(datetime: str):
    return [int(i) for i in datetime.split('-')]


def get_nano_timestamp(year, month, day, hour, minute, second):
    '''
    The Kraken API Trades endpoint takes nanosecond timestamps, e.g. 1738022400000000000.
    '''
    date = datetime.datetime(year, month, day, hour, minute, second)
    return int(time.mktime(date.timetuple()) * 1000000000)


def get_second_timestamp(year, month, day, hour, minute, second):
    '''
    The Kraken API Trades endpoint returns timestamps in seconds (with fractional part in
    microseconds), e.g. 1738022410.0468764.

    This is the format in which timestamps are saved in the Trades database table.
    '''
    date = datetime.datetime(year, month, day, hour, minute, second)
    return float(time.mktime(date.timetuple()))
