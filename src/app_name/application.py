"""Satellite analytics engine."""

import argparse
from inspect import getmembers, isfunction
from os import path
import yaml
import orekit
import app_name.apps as apps
from .utils import configure_logging


def parseArgs() -> tuple[argparse.Namespace, dict]:
    """Parse commandline arguments.

    Returns:
        argparse.Namespace: the parsed arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o", "--output", help="Output html file.", type=str, default="index.html"
    )
    parser.add_argument(
        "-c",
        "--config",
        help="path to the configuration yaml file",
        type=str,
        default="config.yaml",
    )

    applist = [m[0] for m in getmembers(apps, isfunction)]
    parser.add_argument(
        "-t",
        "--run-tool",
        help=f"Run a specific tool (default={applist[0] if len(applist) > 0 else 'None'})",
        metavar="tool",
        choices=applist,
        dest="tool",
        default=applist[0] if len(applist) == 1 else None,
    )
    parser.add_argument(
        "--test", help="Run in test-mode.", action="store_true", default=False
    )

    loglevel = parser.add_argument_group(
        title="Log level", description="Set detail level of log output."
    ).add_mutually_exclusive_group()
    loglevel.add_argument(
        "--quiet",
        action="store_const",
        const="CRITICAL",
        dest="loglevel",
        help="Suppress all but the most critical log statements.",
    )
    loglevel.add_argument(
        "--error",
        action="store_const",
        const="ERROR",
        dest="loglevel",
        help="Display error logs.",
    )
    loglevel.add_argument(
        "--warn",
        action="store_const",
        const="WARNING",
        dest="loglevel",
        help="Display error and warning logs.",
    )
    loglevel.add_argument(
        "--info",
        action="store_const",
        const="INFO",
        dest="loglevel",
        help="Print informational logging.",
    )
    loglevel.add_argument(
        "--debug",
        action="store_const",
        const="DEBUG",
        dest="loglevel",
        help="Display highly detailed level of logging.",
    )

    ##
    # TODO: add more command line args here
    #
    ##

    args = parser.parse_args()

    if args.config and path.exists(args.config):
        with open(args.config, "r") as file:
            config = yaml.safe_load(file)
    else:
        config = {}

    return (args, config)


def runApp(vm=None):
    """Run the specified application.

    Args:
        vm (Any): The orekit vm handle.

    Raises:
        ValueError: When an unknown application is specified.

    Returns:
        _type_: _description_
    """
    if vm is None:
        vm = orekit.initVM()
    
    import orekitfactory

    (args, config) = parseArgs()

    configure_logging(args.loglevel or "INFO")

    # initOrekit(config["orekit"])
    if config and "orekit" in config and "data" in config["orekit"]:
        orekitfactory.init_orekit(source=config["orekit"]["data"])
    else:
        orekitfactory.init_orekit()

    for name, method in getmembers(apps, isfunction):
        if name == args.tool:
            return method(vm=vm, args=args, config=config)

    raise ValueError(f"cannot run unknown tool: {args.tool}")
