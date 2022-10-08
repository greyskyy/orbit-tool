"""Check astropy's GCRF -> ITRF transformations."""
import logging
import orekitfactory

import orbit_tool.utils as utils

import pandas

from org.orekit.data import DataContext
from org.orekit.orbits import OrbitType
from org.orekit.time import AbsoluteDate

import astropy.coordinates
import astropy.time
import astropy.units

SUBCOMMAND = "check-astropy"
ALIASES = ["ca"]


def execute(vm=None, args=None, config=None) -> int:
    logger = logging.getLogger(__name__)
    context = DataContext.getDefault()

    df = build_data_frame(config, context)
    add_astropy_cols(df)

    df["itrf_diff_x"] = df["itrf_x"] - df["itrs_x"]
    df["itrf_diff_y"] = df["itrf_y"] - df["itrs_y"]
    df["itrf_diff_z"] = df["itrf_z"] - df["itrs_z"]

    df["itrf_diff_dx"] = df["itrf_dx"] - df["itrs_dx"]
    df["itrf_diff_dy"] = df["itrf_dy"] - df["itrs_dy"]
    df["itrf_diff_dz"] = df["itrf_dz"] - df["itrs_dz"]

    diff_itrf_pos = astropy.coordinates.CartesianRepresentation(
        x=df["itrf_diff_x"], y=df["itrf_diff_y"], z=df["itrf_diff_z"]
    )

    diff_itrf_vel = astropy.coordinates.CartesianRepresentation(
        x=df["itrf_diff_dx"], y=df["itrf_diff_dy"], z=df["itrf_diff_dz"]
    )

    df["delta_itrf_pos"] = diff_itrf_pos.norm().value
    df["delta_itrf_vel"] = diff_itrf_vel.norm().value

    print(df[["delta_itrf_pos", "delta_itrf_vel"]].describe())


def add_astropy_cols(df: pandas.DataFrame):
    j2000 = astropy.time.Time("2000-01-01T12:00:00", format="isot", scale="tt")
    time = j2000.tai + astropy.time.TimeDelta(
        df["j2000_sec"], format="sec", scale="tai"
    )

    posvel = astropy.coordinates.CartesianRepresentation(
        x=df["gcrf_x"],
        y=df["gcrf_y"],
        z=df["gcrf_z"],
        unit=astropy.units.m,
        differentials=astropy.coordinates.CartesianDifferential(
            d_x=df["gcrf_dx"],
            d_y=df["gcrf_dy"],
            d_z=df["gcrf_dz"],
            unit=astropy.units.m / astropy.units.s,
        ),
    )

    gcrs = astropy.coordinates.GCRS(posvel, obstime=time)
    itrs = gcrs.transform_to(astropy.coordinates.ITRS(obstime=time))

    df["itrs_x"] = list(itrs.x)
    df["itrs_y"] = list(itrs.y)
    df["itrs_z"] = list(itrs.z)
    df["itrs_dx"] = list(itrs.v_x)
    df["itrs_dy"] = list(itrs.v_y)
    df["itrs_dz"] = list(itrs.v_z)


def build_data_frame(config: dict, context: DataContext) -> pandas.DataFrame:

    # load a consistent earth model
    earth = orekitfactory.get_reference_ellipsoid(
        model="wgs84", frame="itrf", iersConventions="2010", simpleEop=False
    )

    orbit, type = utils.read_orbit(orbit_name="orbit3", config=config["orbits"])

    propagator = orekitfactory.to_propagator(
        orbit,
        centralBody=earth,
        context=context,
        orbitType=OrbitType.CARTESIAN,
        **config["propagator_args"],
    )

    start: AbsoluteDate = orbit.getDate()
    isodate = []
    j2000_sec = []
    gcrf_x = []
    gcrf_y = []
    gcrf_z = []
    gcrf_dx = []
    gcrf_dy = []
    gcrf_dz = []
    itrf_x = []
    itrf_y = []
    itrf_z = []
    itrf_dx = []
    itrf_dy = []
    itrf_dz = []

    orekit_gcrf = context.getFrames().getGCRF()
    orekit_itrf = orekitfactory.get_frame(
        "itrf", context=context, simpleEop=False, iersConventions="2010"
    )

    for dt in range(0, 86400, 600):
        date = start.shiftedBy(float(dt))
        state = propagator.propagate(date)
        pv_gcrf = state.getPVCoordinates(orekit_gcrf)
        pv_itrf = state.getPVCoordinates(orekit_itrf)

        isodate.append(str(date.toString()))
        j2000_sec.append(date.durationFrom(AbsoluteDate.J2000_EPOCH))

        gcrf_x.append(pv_gcrf.getPosition().getX() * astropy.units.m)
        gcrf_y.append(pv_gcrf.getPosition().getY() * astropy.units.m)
        gcrf_z.append(pv_gcrf.getPosition().getZ() * astropy.units.m)
        gcrf_dx.append(pv_gcrf.getVelocity().getX() * astropy.units.m / astropy.units.s)
        gcrf_dy.append(pv_gcrf.getVelocity().getY() * astropy.units.m / astropy.units.s)
        gcrf_dz.append(pv_gcrf.getVelocity().getZ() * astropy.units.m / astropy.units.s)

        itrf_x.append(pv_itrf.getPosition().getX() * astropy.units.m)
        itrf_y.append(pv_itrf.getPosition().getY() * astropy.units.m)
        itrf_z.append(pv_itrf.getPosition().getZ() * astropy.units.m)
        itrf_dx.append(pv_itrf.getVelocity().getX() * astropy.units.m / astropy.units.s)
        itrf_dy.append(pv_itrf.getVelocity().getY() * astropy.units.m / astropy.units.s)
        itrf_dz.append(pv_itrf.getVelocity().getZ() * astropy.units.m / astropy.units.s)

    return pandas.DataFrame(
        {
            "isodate": isodate,
            "j2000_sec": j2000_sec,
            "gcrf_x": gcrf_x,
            "gcrf_y": gcrf_y,
            "gcrf_z": gcrf_z,
            "gcrf_dx": gcrf_dx,
            "gcrf_dy": gcrf_dy,
            "gcrf_dz": gcrf_dz,
            "itrf_x": itrf_x,
            "itrf_y": itrf_y,
            "itrf_z": itrf_z,
            "itrf_dx": itrf_dx,
            "itrf_dy": itrf_dy,
            "itrf_dz": itrf_dz,
        }
    )
