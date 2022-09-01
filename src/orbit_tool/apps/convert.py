"""Convert from one orbit format to another format."""
import logging

import orbit_tool.utils.orbit_reader as orbit_reader

SUBCOMMAND = "convert-orbit"


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
        choices=["tle", "keplerian"],
        default="keplerian",
        help="Specify the output orbit format.",
    )


def execute(vm=None, args=None, config=None) -> int:
    """An example application.

    This function performs a basic thing that does stuff.
    """
    logger = logging.getLogger(__name__)

    orbit, type = orbit_reader.read_orbit(
        orbit_name=args.orbit, config=config["orbits"]
    )
    print(f"converting {type} to {args.to}")

    logger.info("completed.")
    return 0
