import datetime
import time


def parse_datetime(datetime: str):
    return [int(i) for i in datetime.split('-')]


def get_timestamp(year, month, day, hour, minute, second):
    date = datetime.datetime(year, month, day, hour, minute, second)
    return int(time.mktime(date.timetuple()) * 1000000000)
