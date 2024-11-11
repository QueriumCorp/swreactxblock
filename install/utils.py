# -*- coding: utf-8 -*-
"""Install utilities for the stepwise-power-xblock XBlock."""

import os


def logger(msg: str):
    """
    Print a message to the console.
    """
    prefix = "stepwise-power-xblock"
    print(prefix + ": " + msg)


def validate_path(path):
    """
    Check if a path exists, and raise an exception if it does not.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"copy_assets() path not found: {path}")
    logger("copy_assets() validated path: " + path)
