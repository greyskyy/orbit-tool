"""Test appliction.
Running this script simulates a build + install + run of the module.
"""
from app_name.application import runApp
import sys

if __name__ == "__main__":
    rc = runApp()
    sys.exit(rc)
