from datetime import timedelta
import isodate


def to_timedelta(value) -> timedelta:
    if value is None:
        return timedelta()
    elif isinstance(value, timedelta):
        return value
    elif isinstance(value, str):
        return isodate.parse_duration(value)
    elif isinstance(value, int) or isinstance(value, float):
        return timedelta(seconds=float(value))
    else:
        raise ValueError(f"Failed to convert value to timedelta. Value={value}")
