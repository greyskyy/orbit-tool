"""Generate an HTML file, drawing the orbit around a cesium globe."""
from typing import Generator
import czml3
import czml3.enums
import czml3.properties
import czml3.types
import orekitfactory
import datetime


import orbit_tool.utils as utils

from orekit.pyhelpers import absolutedate_to_datetime

from org.orekit.data import DataContext
from org.orekit.orbits import OrbitType
from org.orekit.time import AbsoluteDate

SUBCOMMAND = "draw-orbit"
ALIASES = ["show-orbit", "show"]


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


def execute(vm=None, args=None, config=None) -> int:
    """Generate the orbit html."""

    packet, start, stop = generate_packet(args, config)

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
            packet,
        ]
    )

    with open(args.output_file, "w") as f:
        doc.dump(f)


def generate_packet(
    args, config
) -> tuple[czml3.Packet, datetime.datetime, datetime.datetime]:
    context = DataContext.getDefault()

    # load a consistent earth model
    earth = orekitfactory.get_reference_ellipsoid(
        model="wgs84", frame="itrf", iersConventions="2010", simpleEop=False
    )

    orbit, type = utils.read_orbit(orbit_name=args.orbit, config=config["orbits"])

    propagator = orekitfactory.to_propagator(
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

    packet = czml3.Packet(
        id=args.orbit,
        name=name,
        availability=czml3.types.TimeInterval(start=start_dt, end=stop_dt),
        billboard=bb,
        label=label,
        path=path,
        position=pos,
    )

    return packet, start_dt, stop_dt


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
