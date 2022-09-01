from enum import Enum, auto

from org.orekit.data import DataContext
from org.orekit.orbits import Orbit
from org.orekit.propagation.analytical.tle import TLE

import logging
import orekitfactory
import requests


class OrbitType(Enum):
    TLE = auto()
    KEPLERIAN = auto()


def read_orbit(
    orbit_name: str = None, config: dict = None, context: DataContext = None, **kwargs
) -> tuple[Orbit | TLE, OrbitType]:
    """Read an orbit based on the orbit name

    Args:
        orbit_name (str): _description_
        config (dict): _description_

    Raises:
        ValueError: _description_

    Returns:
        tuple[Orbit | TLE, OrbitType]: _description_
    """
    orbit_def = {}
    if orbit_name:
        orbit_def = config[orbit_name]

        if not orbit_def:
            raise ValueError(f"No orbit definition found for {orbit_name}.")

    if "catnr" in orbit_def:
        return (
            _load_tle_from_catalog(orbit_def["catnr"], context=context),
            OrbitType.TLE,
        )
    elif "line1" in orbit_def:
        return (
            orekitfactory.to_tle(
                orbit_def["line1"], orbit_def["line2"], context=context
            ),
            OrbitType.TLE,
        )
    elif "a" in orbit_def:
        return (
            orekitfactory.to_orbit(**orbit_def, context=context),
            OrbitType.KEPLERIAN,
        )
    else:
        logging.getLogger(__name__).warn("Unable to load orbit for defintion")

        return (None, None)


def _load_tle_from_catalog(catnr, context: DataContext = None) -> TLE:
    catnr = int(catnr)
    r = requests.get(
        f"https://celestrak.com/NORAD/elements/gp.php?CATNR={catnr}&FORMAT=TLE",
        headers={
            "accept": "*/*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36",  # noqa: E501
        },
    )
    if not r.status_code == 200:
        logging.getLogger(__name__).error(
            "Failed to load tle for catnr %d. HTTP return code: %d",
            catnr,
            r.status_code,
        )
        raise RuntimeError(f"failed to load TLE for catalog number {catnr}")

    data = r.content.splitlines()
    return orekitfactory.to_tle(data[1], data[2], context=context)
