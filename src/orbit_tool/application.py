"""Satellite analytics engine."""

import argparse
import importlib
import pkgutil
import inspect
from os import path
import sys
import yaml
import orekit

from .logging import configure_logging


def parseArgs() -> tuple[argparse.Namespace, dict]:
    """Parse commandline arguments.

    Returns:
        argparse.Namespace: the parsed arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config",
        help="path to the configuration yaml file",
        type=str,
        default="config.yaml",
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

    subparsers = parser.add_subparsers(
        title="Subcommands",
        description="Valid subcommands.",
        help="Specify {subcommand} --help for more details",
    )

    for module_loader, name, ispkg in pkgutil.iter_modules(
        importlib.import_module("orbit_tool.apps").__path__, "orbit_tool.apps."
    ):
        app_module = importlib.import_module(name)
        helpstr = ""
        func = None
        conf = None
        command = name.replace("orbit_tool.apps.", "")
        aliases = []

        for n, value in inspect.getmembers(app_module):
            if n == "__doc__":
                helpstr = value
            elif n == "SUBCOMMAND":
                command = value
            elif n == "config_args":
                conf = value
            elif n == "execute":
                func = value
            elif n == "ALIASES":
                aliases = value

        if func:
            p = subparsers.add_parser(command, help=helpstr, aliases=aliases)
            if conf:
                conf(p)
            p.set_defaults(func=func)

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
    from orekitfactory.utils import Dataloader

    Dataloader.data_dir = ".data"

    (args, config) = parseArgs()

    configure_logging(args.loglevel or "INFO")

    # initOrekit(config["orekit"])
    if config and "orekit" in config and "data" in config["orekit"]:
        orekitfactory.init_orekit(source=config["orekit"]["data"])
    else:
        orekitfactory.init_orekit()

    if "func" in args:
        return args.func(vm=vm, args=args, config=config)
    else:
        print("No subcommand specified. Use --help for more info", file=sys.stderr)
