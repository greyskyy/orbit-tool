"""Example application."""
import logging


def example_app(vm=None, args=None, config=None) -> int:
    """An example application.

    This function performs a basic thing that does stuff.
    """
    logger = logging.getLogger(__name__)

    print(f"vm={vm}")
    print("Yay example!")

    logger.info("completed.")
    return 0
