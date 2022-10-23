"""Test appliction.
Running this script simulates a build + install + run of the module.
"""
import pyrebar
import pyrebar.application
import sys


if sys.version_info < (3, 10):
    from importlib_metadata import EntryPoint
else:
    from importlib.metadata import EntryPoint

if __name__ == "__main__":
    # pre-init plugins
    pyrebar.Plugins.add_entrypoint(
        EntryPoint(
            name="config-args",
            value="orbit_tool.configuration:add_args",
            group=pyrebar.Plugins.PREINIT_GROUP,
        )
    )
    
    # post-init plugins
    pyrebar.Plugins.add_entrypoint(
        EntryPoint(
            name="config-load",
            value="orbit_tool.configuration:load_config",
            group=pyrebar.Plugins.POSTINIT_GROUP,
        )
    )

    # apps
    pyrebar.Plugins.add_entrypoint(EntryPoint(
        name="check-tle",
        value="orbit_tool.apps.checktle",
        group=pyrebar.Plugins.APP_GROUP,
    ))
    
    pyrebar.Plugins.add_entrypoint(EntryPoint(
        name="compare-orbits",
        value="orbit_tool.apps.compare_orbits",
        group=pyrebar.Plugins.APP_GROUP,
    ))
    
    pyrebar.Plugins.add_entrypoint(EntryPoint(
        name="convert",
        value="orbit_tool.apps.convert",
        group=pyrebar.Plugins.APP_GROUP,
    ))
    
    pyrebar.Plugins.add_entrypoint(EntryPoint(
        name="draw-orbit",
        value="orbit_tool.apps.draw_orbit",
        group=pyrebar.Plugins.APP_GROUP,
    ))
    
    pyrebar.Plugins.add_entrypoint(EntryPoint(
        name="verify-astropy",
        value="orbit_tool.apps.verify_astropy",
        group=pyrebar.Plugins.APP_GROUP,
    ))
    
    rc = pyrebar.application.main()
    sys.exit(rc)
