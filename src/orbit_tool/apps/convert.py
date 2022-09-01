"""Example application."""
import logging

from orbit_tool.utils import read_orbit

def convert(vm=None, args=None, config=None) -> int:
    """An example application.

    This function performs a basic thing that does stuff.
    """
    logger = logging.getLogger(__name__)

    orbit, type = read_orbit(orbit_name=args.orbit, config=config["orbits"])
    print(f"converting {type} to {args.to}")

    logger.info("completed.")
    return 0
