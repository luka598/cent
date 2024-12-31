from cent.rhythm.unit import Seconds, Timestamp


def floor_time(time: Timestamp, time_unit: Seconds) -> Timestamp:
    return time - (time % time_unit)


def floor_minute(time: Timestamp) -> Timestamp:
    return floor_time(time, 60)
