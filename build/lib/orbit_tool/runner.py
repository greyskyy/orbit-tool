"""Initialize and run the satellite scheduler application."""
import pyrebar

def run():
    rc = pyrebar.main(plugin_prefix="orbittool")
    return rc
