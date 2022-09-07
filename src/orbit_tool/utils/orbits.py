import astropy.units as u
import json
from org.orekit.orbits import (
    Orbit,
    PositionAngle,
    KeplerianOrbit,
    CircularOrbit,
    EquinoctialOrbit,
)
from org.orekit.propagation.analytical.tle import TLE
from org.hipparchus.util import MathUtils, FastMath

from orekitfactory.utils import validate_quantity

from .orbit_reader import OrbitType


def orbit_to_dict(orbit: TLE | Orbit, dest_type: OrbitType, config: dict) -> dict:
    if isinstance(orbit, TLE):
        return {"line1": orbit.getLine1(), "line2": orbit.getLine2()}
    elif isinstance(orbit, Orbit):
        
        if dest_type is OrbitType.AUTO_SELECT:
            if isinstance(orbit, KeplerianOrbit):
                dest_type = OrbitType.KEPLERIAN
            elif isinstance(orbit, CircularOrbit):
                dest_type = OrbitType.CIRCULAR
            elif isinstance(orbit, EquinoctialOrbit):
                dest_type = OrbitType.EQUINOCTIAL
            else:
                orbit = KeplerianOrbit(orbit)
                circular_threshold = float(config.get("circular_threshold", 1.0e-3))
                equatoral_threshold = validate_quantity(config.get("equatoral_threshold", 0.001), u.deg)
                
                circular = orbit.getE() < circular_threshold
                equatoral = orbit.getI() < float(equatoral_threshold.to_value(u.rad))
                
                if circular and not equatoral:
                    dest_type = OrbitType.CIRCULAR
                elif circular or equatoral:
                    dest_type = OrbitType.EQUINOCTIAL
                else:
                    dest_type = OrbitType.KEPLERIAN
        
        if dest_type is OrbitType.KEPLERIAN:
            orbit = KeplerianOrbit(orbit)
            return {
                "a": u.Quantity(orbit.getA(), u.m).to_string(u.km),
                "e": orbit.getE(),
                "i": u.Quantity(orbit.getI(), u.rad).to_string(u.deg),
                "w": u.Quantity(orbit.getPerigeeArgument(), u.rad).to_string(u.deg),
                "omega": u.Quantity(
                    MathUtils.normalizeAngle(
                        orbit.getRightAscensionOfAscendingNode(), FastMath.PI
                    ),
                    u.rad,
                ).to_string(u.deg),
                "v": u.Quantity(
                    MathUtils.normalizeAngle(orbit.getTrueAnomaly(), FastMath.PI), u.rad
                ).to_string(u.deg),
                "m": u.Quantity(
                    MathUtils.normalizeAngle(orbit.getMeanAnomaly(), FastMath.PI), u.rad
                ).to_string(u.deg),
            }
        elif dest_type is OrbitType.CIRCULAR:
            orbit = CircularOrbit(orbit)
            return {
                "a": u.Quantity(orbit.getA(), u.m).to_string(u.km),
                "ex": orbit.getCircularEx(),
                "ey": orbit.getCircularEy(),
                "i": u.Quantity(orbit.getI(), u.rad).to_string(u.deg),
                "omega": u.Quantity(
                    MathUtils.normalizeAngle(
                        orbit.getRightAscensionOfAscendingNode(), FastMath.PI
                    ),
                    u.rad,
                ).to_string(u.deg),
                "alphaV": u.Quantity(
                    MathUtils.normalizeAngle(orbit.getAlphaV(), FastMath.PI), u.rad
                ).to_string(u.deg)
            }

    raise ValueError(
        f"Cannot convert orbit {str(orbit)} to destination type {dest_type}."
    )
