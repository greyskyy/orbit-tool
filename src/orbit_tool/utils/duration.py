from datetime import timedelta
import argparse
import isodate
import logging
import orekitfactory

import orbit_tool.utils as utils
from org.orekit.time import AbsoluteDate


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


def start_stop_step(
    args: argparse.Namespace, config: dict, orbitdate: AbsoluteDate
) -> tuple[AbsoluteDate, AbsoluteDate, timedelta]:
    # compute propagation step
    if args.step:
        step = to_timedelta(args.step)
    elif "step" in config:
        step = to_timedelta(config["step"])
    else:
        step = timedelta(minutes=10)

    if step <= timedelta():
        raise RuntimeError("Invalid step. Durations must be greater than zero.")

    # start-date
    if "start" in args:
        start_date = orekitfactory.to_absolute_date(args.start)
    elif "start" in config:
        start_date = orekitfactory.to_absolute_date(config["start"])
    else:
        start_date = orbitdate

    # compute the stop
    if args.duration:
        stop_date = start_date.shiftedBy(to_timedelta(args.duration).total_seconds())
    elif "duration" in config:
        stop_date = start_date.shiftedBy(
            to_timedelta(config["duration"]).total_seconds()
        )
    elif "stop" in args:
        stop_date = orekitfactory.to_absolute_date(args.stop)
    else:
        stop_date = start_date.shiftedBy(timedelta(weeks=2).total_seconds())

    if start_date.isAfterOrEqualTo(stop_date):
        logging.getLogger(__name__).debug(
            "start=%s, stop=%s", start_date.toString(), stop_date.toString()
        )
        raise RuntimeError("stop date must be after start date")

    return start_date, stop_date, step
