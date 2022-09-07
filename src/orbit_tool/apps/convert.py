"""Convert from one orbit format to another format."""
from datetime import timedelta
import logging
import json

import orbit_tool.utils as utils

import orekitfactory

from java.util import ArrayList
from org.orekit.data import DataContext
from org.orekit.forces.drag import DragSensitive
from org.orekit.orbits import PositionAngle, OrbitType, KeplerianOrbit
from org.orekit.propagation import SpacecraftState, Propagator
from org.orekit.propagation.analytical.tle import TLEPropagator, TLE
from org.orekit.propagation.conversion import (
    DormandPrince853IntegratorBuilder,
    KeplerianPropagatorBuilder,
    PropagatorBuilder,
    PropagatorConverter,
    TLEPropagatorBuilder,
    NumericalPropagatorBuilder,
    
    FiniteDifferencePropagatorConverter,
)
from org.orekit.time import AbsoluteDate

SUBCOMMAND = "convert-orbit"
ALIASES = ["co"]


def config_args(parser):
    parser.add_argument(
        "--from",
        type=str,
        required=True,
        dest="orbit",
        help="Specify the orbit from the config file on which to operate.",
    )
    parser.add_argument(
        "--to",
        type=str,
        choices=[t.name.lower() for t in utils.OrbitType],
        default=utils.OrbitType.AUTO_SELECT.name.lower(),
        help="Specify the output orbit format.",
    )

    parser.add_argument(
        "--seed-orbit",
        type=str,
        dest="seed_orbit",
        help="An orbit definition used to seed the orbit solver. Must be the same type as the destination orbit.",
    )

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


def generate_states(
    propgator: Propagator,
    start_date: AbsoluteDate,
    stop_date: AbsoluteDate,
    step: timedelta,
) -> ArrayList:
    logger = logging.getLogger(__name__)

    logger.debug(
        "Starting propagation start=%s stop=%s step=%s",
        start_date.toString(),
        stop_date.toString(),
        step,
    )

    t = start_date
    step_secs = step.total_seconds()

    states = ArrayList()
    while t.isBeforeOrEqualTo(stop_date):
        states.add(propgator.propagate(t))
        t = t.shiftedBy(step_secs)

    logger.info("Completed propagation. Generated %d states", states.size())

    return states


def execute(vm=None, args=None, config=None) -> int:
    """An example application.

    This function performs a basic thing that does stuff.
    """
    logger = logging.getLogger(__name__)
    context = DataContext.getDefault()

    # load a consistent earth model
    earth = orekitfactory.get_reference_ellipsoid(
        model="wgs84", frame="itrf", iersConventions="2010", simpleEop=False
    )

    # load source orbit, type, and destination type
    orbit, type = utils.read_orbit(orbit_name=args.orbit, config=config["orbits"])
    dest_type = utils.OrbitType[args.to.upper()]
  
    logger.info("Converting source type=%s to dest_type=%s", type, dest_type)

    if type == dest_type:
        logger.debug("Source and dest are the same. Nothing to do.")
        return 0

    # load the seed orbit
    seed_orbit, seed_type = utils.read_orbit(
        orbit_name=args.seed_orbit, config=config["orbits"]
    )
    if not utils.OrbitType.compatible_with(seed_type, dest_type):
        logger.error(
            "Seed orbit not same as destination. seed=%s, dest=%s", seed_type, dest_type
        )
        raise RuntimeError(
            "Seed orbit must be specified in the same format as destination."
        )

    # start, stop and step for propagation
    start_date, stop_date, step = utils.start_stop_step(args, config, orbit.getDate())

    # create the initial propagator
    propagator = orekitfactory.to_propagator(
        orbit,
        entralBody=earth,
        context=context,
        orbitType=OrbitType.CARTESIAN,
        **config["propagator_args"]
    )

    # propagate to generate states
    states = generate_states(propagator, start_date, stop_date, step)

    new_orbit = None
    if dest_type is utils.OrbitType.TLE:
        seed_orbit = TLE.stateToTLE(states.get(0), seed_orbit)

        builder = TLEPropagatorBuilder(seed_orbit, PositionAngle.TRUE, 1.0, context)
        converter = FiniteDifferencePropagatorConverter(builder, 1e-3, 1000)

        converter.convert(states, False, TLE.B_STAR)

        new_prop: TLEPropagator = TLEPropagator.cast_(converter.getAdaptedPropagator())

        new_orbit = new_prop.getTLE()
    else:
        seed_orbit = SpacecraftState.cast_(states.get(0)).getOrbit()
        dormandBuilder = DormandPrince853IntegratorBuilder(1.0e-3, 600.0, 1.0e-3)
        #builder = KeplerianPropagatorBuilder(seed_orbit, PositionAngle.TRUE, 1.0)
        builder = NumericalPropagatorBuilder(seed_orbit, dormandBuilder, PositionAngle.TRUE, 1.0)
        converter = FiniteDifferencePropagatorConverter(builder, 1e-3, 1000)

        converter.convert(states, False, "central attraction coefficient")

        new_prop = converter.getAdaptedPropagator()

        state = new_prop.propagate(start_date)

        new_orbit = state.getOrbit()
    
    print("")
    print("Generated Orbit:")
    print("")
    print(json.dumps(utils.orbit_to_dict(new_orbit, dest_type, config), indent=2))
    print("")

    logger.info("completed.")
    return 0

