"""Compare 2 different orbits over time."""
from datetime import timedelta
import argparse
import logging
import orekitfactory.factory
import astropy.units as u
import matplotlib.pyplot as plt
import orbit_tool.utils as utils

from org.orekit.data import DataContext
from org.orekit.orbits import OrbitType

from .checktle import compare_propagators
from ..configuration import get_config

ALIASES = ["compare", "comp", "cmp"]
LOGGER_NAME = "orbit_tool"


def config_args(parser):
    parser.add_argument(
        "orbits",
        type=str,
        nargs=2,
        help="The first orbit to check.",
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
    earth = orekitfactory.factory.get_reference_ellipsoid(
        model="wgs84", frame="itrf", iersConventions="2010", simpleEop=False
    )

    # load the tle
    (orbit1, orbittype1) = utils.read_orbit(
        orbit_name=args.orbits[0], config=config["orbits"], context=context
    )

    (orbit2, orbittype2) = utils.read_orbit(
        orbit_name=args.orbits[1], config=config["orbits"], context=context
    )
    # start, stop, and step
    start_date, stop_date, step = utils.start_stop_step(args, config, orbit1.getDate())

    logger.debug("Exection start time set to %s", str(start_date))

    # build the propagators
    propagator1 = orekitfactory.factory.to_propagator(
        orbit1,
        centralBody=earth,
        context=context,
        orbitType=OrbitType.CARTESIAN,
        **config["propagator_args"],
    )
    propagator2 = orekitfactory.factory.to_propagator(
        orbit2,
        centralBody=earth,
        context=context,
        orbitType=OrbitType.CARTESIAN,
        **config["propagator_args"],
    )

    data = compare_propagators(
        propagator1,
        propagator2,
        start_date,
        stop_date,
        step,
        context.getFrames().getGCRF(),
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
