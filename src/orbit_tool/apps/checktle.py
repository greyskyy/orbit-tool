"""Verify a TLE's accuracy over time against a high fidelity propatator."""
from datetime import timedelta
import argparse
import logging
import orekitfactory.factory
import astropy.units as u
import matplotlib.pyplot as plt
import time

from org.orekit.data import DataContext
from org.orekit.frames import Frame, LOFType
from org.orekit.orbits import CartesianOrbit
from org.orekit.propagation import Propagator
from org.orekit.time import AbsoluteDate

from ..configuration import get_config
from ..utils import read_orbit, OrbitType, to_timedelta, start_stop_step

from pandas import DataFrame


ALIASES = ["check", "chk"]
LOGGER_NAME = "orbit_tool"


def config_args(parser):
    parser.add_argument(
        "--orbit",
        type=str,
        required=True,
        dest="orbit",
        help="Specify the tle orbit to check.",
    )

    ## TODO: add inline catnr / orbit definition

    parser.add_argument(
        "-d",
        "--duration",
        type=str,
        dest="duration",
        help="The propagation duration, specified either as an ISO-8601 duration or number of seconds. Overrides the value from the config file.",
    )

    parser.add_argument(
        "-s",
        "--step",
        type=str,
        dest="step",
        help="The propagation duration, specified either as an ISO-8601 duration or number of seconds. Overrides the value from the config file.",
    )

    parser.add_argument(
        "--display",
        action=argparse.BooleanOptionalAction,
        dest="display",
        help="Display the results graphically.",
        default="true",
    )

    parser.add_argument(
        "--summary",
        action=argparse.BooleanOptionalAction,
        dest="summary",
        default=True,
        help="Enable (or suppress) summary output after a run.",
    )

    out_group = parser.add_mutually_exclusive_group()
    out_group.add_argument(
        "-o",
        "--output-format",
        type=str,
        choices=["none", "csv"],
        default="none",
        dest="format",
        help="Define the output format (or suppress it).",
    )
    out_group.add_argument(
        "-O",
        "--no-output",
        action="store_const",
        dest="format",
        const="none",
        help="Do not write an output file. Equivalent to -o none.",
    )

    out_group.add_argument(
        "--csv",
        action="store_const",
        const="csv",
        dest="format",
        help="Specify output as CSV. Equivalent to -o csv",
    )

    parser.add_argument(
        "-f",
        "--file",
        dest="file",
        default="outfile",
        help="Path to write output.",
    )


def execute(args=None) -> int:
    """Compare propagation of a tle against a high-fidelity propagator."""

    logger = logging.getLogger(__name__)
    context = DataContext.getDefault()
    config = get_config()

    # load a consistent earth model
    earth = orekitfactory.get_reference_ellipsoid(
        model="wgs84", frame="itrf", iersConventions="2010", simpleEop=False
    )

    # load the tle
    (tle, orbittype) = read_orbit(
        orbit_name=args.orbit, config=config["orbits"], context=context
    )

    if not orbittype == OrbitType.TLE:
        logger.error(
            "Loaded orbit is not a TLE. orbit=%s, type=%s", args.orbit, str(orbittype)
        )
        raise RuntimeError(
            "Orbit is not a TLE. Specify orbit as a TLE or select a different tool."
        )

    logger.info("Successfully loaded TLE for %s", args.orbit)

    # start, stop, and step
    start_date, stop_date, step = start_stop_step(args, config, tle.getDate())

    logger.debug("Exection start time set to %s", str(start_date))

    # build the TLE's SGP4 propagator
    sgp4 = orekitfactory.factory.to_propagator(
        tle, centralBody=earth, context=context, **config["propagator_args"]
    )

    # build an orbit from the initial state
    initial_state = sgp4.propagate(start_date)
    cart_orbit = CartesianOrbit(
        initial_state.getPVCoordinates(), initial_state.getFrame(), earth.getGM()
    )

    # build the orbit from the cartesian orbit
    cart_prop = orekitfactory.factory.to_propagator(
        cart_orbit, centralBody=earth, context=context, **config["propagator_args"]
    )

    data = compare_propagators(
        cart_prop, sgp4, start_date, stop_date, step, context.getFrames().getGCRF()
    )

    if args.summary:
        max_error = data.max(numeric_only=True).drop(labels="date_secs")
        max_error = max_error.apply(lambda x: u.Quantity(x, u.km))
        print(max_error)

    if args.format != "none":
        fname: str = args.file
        if not fname.endswith(f".{args.format}"):
            fname = f"{fname}.{args.format}"

        data.to_csv(fname, encoding="utf-8")

    if args.display:
        data.plot(x="date_secs", y=["radial_err", "in_track_err", "cross_track_err"])
        plt.show()


def compare_propagators(
    base: Propagator,
    check: Propagator,
    start: AbsoluteDate,
    stop: AbsoluteDate,
    step: timedelta,
    frame: Frame,
) -> DataFrame:
    logger = logging.getLogger(__name__)

    logger.info(
        "Starting execution start=%s, stop=%s, step=%s",
        str(start),
        str(stop),
        str(step),
    )
    dates = []
    date_secs = []
    in_track_err = []
    cross_track_err = []
    radial_err = []

    if step <= timedelta():
        raise RuntimeError("Invalid step. Durations must be greater than zero.")

    t = start
    step_secs = step.total_seconds()
    count = 0
    perf_t0 = time.perf_counter_ns()
    while t.isBeforeOrEqualTo(stop):
        if 0 == count % 100:
            logger.debug("evaluating for t=%s", str(t))

        base_state = base.propagate(t)
        check_state = check.propagate(t)

        base_pv = base_state.getPVCoordinates(frame)
        check_pv = check_state.getPVCoordinates(frame)

        tx_to_lof = LOFType.QSW.transformFromInertial(t, base_pv)

        check_pv_lof = tx_to_lof.transformPVCoordinates(check_pv)

        dates.append(str(t))
        date_secs.append(t.durationFrom(start))
        radial_err.append(check_pv_lof.getPosition().getX() / 1000.0)
        in_track_err.append(check_pv_lof.getPosition().getY() / 1000.0)
        cross_track_err.append(check_pv_lof.getPosition().getZ() / 1000.0)

        t = t.shiftedBy(step_secs)
        count = count + 1
    perf_t1 = time.perf_counter_ns()

    logger.info(
        "Completed propagation in %s.",
        str(timedelta(seconds=(perf_t1 - perf_t0) * 1e-9)),
    )

    return DataFrame.from_dict(
        {
            "dates": dates,
            "date_secs": date_secs,
            "in_track_err": in_track_err,
            "cross_track_err": cross_track_err,
            "radial_err": radial_err,
        }
    )
