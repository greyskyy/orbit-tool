"""Generate an HTML file, drawing the orbit around a cesium globe."""
from typing import Generator
import argparse
import czml3
import czml3.enums
import czml3.properties
import czml3.types
import orekitfactory.factory
import datetime
import orekitfactory.initializer

import orbit_tool.utils as utils

from orekit.pyhelpers import absolutedate_to_datetime

from org.hipparchus.ode.events import Action
from org.orekit.bodies import OneAxisEllipsoid
from org.orekit.data import DataContext
from org.orekit.orbits import Orbit, OrbitType
from org.orekit.propagation.analytical.tle import TLE
from org.orekit.propagation.events import (
    NodeDetector,
    EventDetector,
    LatitudeCrossingDetector,
    LatitudeExtremumDetector,
)
from org.orekit.propagation.events.handlers import EventHandler, PythonEventHandler
from org.orekit.time import AbsoluteDate

from ..configuration import get_config

SUBCOMMAND = "draw-orbit"
ALIASES = ["show-orbit", "show"]
LOGGER_NAME = "orbit_tool"


def config_args(parser):
    parser.add_argument(
        "--output",
        type=str,
        default="orbit.czml",
        dest="output_file",
        help="Output html file",
    )

    parser.add_argument(
        "--orbit",
        type=str,
        required=True,
        dest="orbit",
        help="Specify the orbit to print (the orbit id from config.yaml).",
    )

    parser.add_argument(
        "--duration",
        type=str,
        dest="duration",
        default="PT24H",
        help="Duration of orbit to show, as ISO-8601 duration string (Default PT24H)",
    )

    parser.add_argument(
        "--events",
        action=argparse.BooleanOptionalAction,
        default=False,
        dest="events",
        help="Include (or exclude) orbital events in the displayed output.",
    )


def execute(args=None) -> int:
    """Generate the orbit html."""
    config = get_config()
    packets, start, stop = generate_packet(args, config)

    doc = czml3.Document(
        [
            czml3.Preamble(
                name="orbit-tool-drawing",
                clock=czml3.types.IntervalValue(
                    start=start,
                    end=stop,
                    value=czml3.properties.Clock(currentTime=start, multiplier=10),
                ),
            ),
            *packets,
        ]
    )

    with open(args.output_file, "w") as f:
        doc.dump(f)


def generate_packet(
    args, config
) -> tuple[list[czml3.Packet], datetime.datetime, datetime.datetime]:
    context = DataContext.getDefault()

    # load a consistent earth model
    earth = orekitfactory.factory.get_reference_ellipsoid(
        model="wgs84", frame="itrf", iersConventions="2010", simpleEop=False
    )

    orbit, type = utils.read_orbit(orbit_name=args.orbit, config=config["orbits"])

    propagator = orekitfactory.factory.to_propagator(
        orbit,
        centralBody=earth,
        context=context,
        orbitType=OrbitType.CARTESIAN,
        **config["propagator_args"],
    )

    # start, stop, and step
    start_date, stop_date, step = utils.start_stop_step(args, config, orbit.getDate())
    start_dt = absolutedate_to_datetime(start_date)
    stop_dt = absolutedate_to_datetime(stop_date)

    propagator.propagate(start_date)

    if args.events:
        detectors, handler = _generate_event_detector(
            orbit, body=earth, context=context
        )
        for d in detectors:
            propagator.addEventDetector(d)

    if step <= datetime.timedelta():
        raise RuntimeError("Invalid step. Durations must be greater than zero.")

    def generate_carts():
        inertial = context.getFrames().getGCRF()
        t: AbsoluteDate = start_date
        step_secs: float = step.total_seconds()
        while t.isBeforeOrEqualTo(stop_date):
            state = propagator.propagate(t)

            pv = state.getPVCoordinates(inertial)

            yield t.durationFrom(start_date)
            yield pv.getPosition().getX()
            yield pv.getPosition().getY()
            yield pv.getPosition().getZ()

            t = t.shiftedBy(step_secs)

    name, label, bb = _generate_meta(args.orbit, config["orbits"])
    path = czml3.properties.Path(
        show=czml3.types.Sequence(
            [czml3.types.IntervalValue(start=start_dt, end=stop_dt, value=True)]
        ),
        width=1,
        resolution=120,
        material=czml3.properties.Material(
            solidColor=czml3.properties.SolidColorMaterial(color=label.fillColor)
        ),
    )

    pos = czml3.properties.Position(
        interpolationAlgorithm=czml3.enums.InterpolationAlgorithms.LAGRANGE,
        interpolationDegree=3,
        referenceFrame=czml3.enums.ReferenceFrames.INERTIAL,
        epoch=start_dt,
        cartesian=list(generate_carts()),
    )

    packets = [
        czml3.Packet(
            id=args.orbit,
            name=name,
            availability=czml3.types.TimeInterval(start=start_dt, end=stop_dt),
            billboard=bb,
            label=label,
            path=path,
            position=pos,
        )
    ]

    if args.events:
        for date, event, pv in handler.results:
            show = czml3.types.Sequence(
                [
                    czml3.types.IntervalValue(
                        start=start_dt,
                        end=absolutedate_to_datetime(date.shiftedBy(300.0)),
                        value=False,
                    ),
                    czml3.types.IntervalValue(
                        start=absolutedate_to_datetime(date.shiftedBy(-300.0)),
                        end=absolutedate_to_datetime(date.shiftedBy(300.0)),
                        value=True,
                    ),
                    czml3.types.IntervalValue(
                        start=absolutedate_to_datetime(date.shiftedBy(300.0)),
                        end=stop_dt,
                        value=False,
                    ),
                ]
            )
            packets.append(
                czml3.Packet(
                    id=f"event_{date.toString()}",
                    name=event,
                    label=czml3.properties.Label(
                        font="11pt Lucida Console",
                        text=event,
                        fillColor=czml3.properties.Color.from_str("#00FF00"),
                        style=czml3.enums.LabelStyles.FILL_AND_OUTLINE,
                        show=show,
                    ),
                    position=czml3.properties.Position(
                        cartesian=[
                            pv.getPosition().getX(),
                            pv.getPosition().getY(),
                            pv.getPosition().getZ(),
                        ],
                        referenceFrame=czml3.enums.ReferenceFrames.INERTIAL,
                    ),
                    point=czml3.properties.Point(
                        pixelSize=10,
                        color=czml3.properties.Color.from_str("#00FF00"),
                        outlineColor=czml3.properties.Color.from_str("#00FF00"),
                        outlineWidth=2,
                        show=show,
                    ),
                )
            )

    return packets, start_dt, stop_dt


def _generate_meta(
    orbit_id: str, config: dict
) -> tuple[str, czml3.properties.Label, czml3.properties.Billboard]:
    default_config = config
    orbit_config = config[orbit_id]

    defaults = lambda x, v: orbit_config.get(x, default_config.get(x, v))

    name = orbit_config.get("name", orbit_id)

    label = czml3.properties.Label(
        horizontalOrigin=czml3.enums.HorizontalOrigins.LEFT,
        outlineWidth=defaults("outlineWidth", 2),
        show=True,
        font=defaults("font", "11pt Lucida Console"),
        style=czml3.enums.LabelStyles.FILL_AND_OUTLINE,
        text=name,
        verticalOrigin=czml3.enums.VerticalOrigins.CENTER,
        fillColor=czml3.properties.Color.from_str(defaults("fillColor", "#00FF00")),
        outlineColor=czml3.properties.Color.from_str(
            defaults("outlineColor", "#000000")
        ),
    )

    bb = czml3.properties.Billboard(
        horizontalOrigin=czml3.enums.HorizontalOrigins.CENTER,
        image=(
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9"
            "hAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdv"
            "qGQAAADJSURBVDhPnZHRDcMgEEMZjVEYpaNklIzSEfLfD4qNnXAJSFWfhO7w2Zc0T"
            "f9QG2rXrEzSUeZLOGm47WoH95x3Hl3jEgilvDgsOQUTqsNl68ezEwn1vae6lceSEE"
            "YvvWNT/Rxc4CXQNGadho1NXoJ+9iaqc2xi2xbt23PJCDIB6TQjOC6Bho/sDy3fBQT"
            "8PrVhibU7yBFcEPaRxOoeTwbwByCOYf9VGp1BYI1BA+EeHhmfzKbBoJEQwn1yzUZt"
            "yspIQUha85MpkNIXB7GizqDEECsAAAAASUVORK5CYII="
        ),
        scale=defaults("scale", 1.5),
        show=True,
        verticalOrigin=czml3.enums.VerticalOrigins.CENTER,
    )

    return name, label, bb


class OrbitEventHandler(PythonEventHandler):
    def __init__(self):
        super().__init__()
        self.results = []

    def init(self, initialstate, target, detector):
        """Initialize the handler.

        Args:
            initialstate (SpacecraftState): The spacecraft state.
            target (Any): The target.
            detector (Any): The detector.
        """
        pass

    def resetState(self, detector, oldState):
        """Reset the state.

        Args:
            detector (Any): The detector.
            oldState (Any): The old state.
        """
        pass

    def eventOccurred(self, s, detector, increasing):
        """Process an event.

        Args:
            s (SpacecraftState): Thg spacecraft state at time of event.
            detector (EventDetector): The detector triggering the event.
            increasing (bool): Whether the value is increasing or decreasing.

        Returns:
            _type_: _description_
        """
        frame = DataContext.getDefault().getFrames().getGCRF()
        if detector.getClass().getSimpleName() == "NodeDetector":
            self.results.append(
                [
                    s.getDate(),
                    "ASCENDING_NODE" if increasing else "DESCENDING_NODE",
                    s.getPVCoordinates(frame),
                ]
            )
        elif detector.getClass().getSimpleName() == "LatitudeExtremumDetector":
            self.results.append(
                [
                    s.getDate(),
                    "SOUTH_POINT" if increasing else "NORTH_POINT",
                    s.getPVCoordinates(frame),
                ]
            )
        else:
            print(f"unknown detector provided {detector.getClass().getSimpleName()}")
        return Action.CONTINUE


def _generate_event_detector(
    orbit: Orbit | TLE = None,
    max_check: datetime.timedelta | float = datetime.timedelta(seconds=600),
    threshold: datetime.timedelta | float = datetime.timedelta(microseconds=1),
    body: OneAxisEllipsoid = None,
    context: DataContext = None,
) -> tuple[tuple[EventDetector], OrbitEventHandler]:
    """Compute an event handler suitable for detecting rev-crossing events

    Args:
        type (OrbitEventTypeData): The type of event marking crossings.
        orbit (Orbit|TLE, optional): The orbit definition. Required when looking for ASCENDING or DESCENDING events. Defaults to None.
        max_check (dt.timedelta | float): The maximal checking interval. `float` values will be interpreted as seconds.
        threshold (dt.timedelta | float): The convergence threshold. `float` values will be interpreted as seconds.
        body (OneAxisEllipsoid, optional): The central body around which the satellite orbits. Defaults to None.
        context (DataContext, optional): The context to use. If not provided, the default will be
        used. Defaults to None.

    Raises:
        ValueError: When an invalid type is provided.
    """
    if isinstance(max_check, (int, float)):
        max_check = datetime.timedelta(seconds=max_check)
    if isinstance(threshold, (int, float)):
        threshold = datetime.timedelta(seconds=threshold)

    if body is None:
        body = orekitfactory.factory.get_reference_ellipsoid(context)

    asc_desc_detector = (
        NodeDetector(body.getBodyFrame())
        .withThreshold(threshold.total_seconds())
        .withMaxCheck(max_check.total_seconds())
    )
    north_south_detector = LatitudeExtremumDetector(
        max_check.total_seconds(),
        threshold.total_seconds(),
        OneAxisEllipsoid.cast_(body),
    )

    handler = OrbitEventHandler()
    asc_desc_detector = asc_desc_detector.withHandler(handler)
    north_south_detector = north_south_detector.withHandler(handler)
    return (
        EventDetector.cast_(asc_desc_detector),
        EventDetector.cast_(north_south_detector),
    ), handler
