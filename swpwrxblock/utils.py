# -*- coding: utf-8 -*-
"""Install utilities for the stepwise-power-xblock XBlock."""

import atexit
import os
from datetime import datetime

import pkg_resources

from .const import DEBUG_MODE, PACKAGE_NAME

print("DEBUG: swpwrxblock.utils import successful")


class LoggerBuffer:
    """
    A singleton class to buffer log messages in memory and then write them to a file
    upon destruction.
    """

    _instance = None
    _buffer = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerBuffer, cls).__new__(cls)
            atexit.register(cls._instance.save_logs)
        return cls._instance

    def log(self, msg: str):
        self._buffer.append(msg)

    def get_logs(self):
        return self._buffer

    def clear_logs(self):
        self._buffer = []

    def save_logs(self):
        dist = pkg_resources.get_distribution("stepwise-power-xblock")
        install_path = dist.location
        buffer = self.get_logs()
        log_path = os.path.join(install_path, "post_install.log")

        if os.path.exists(log_path):
            os.remove(log_path)

        with open(log_path, "w", encoding="utf-8") as file:
            for line in buffer:
                file.write(line + "\n")
            file.flush()
            os.fsync(file.fileno())
        self.clear_logs()


def logger(msg: str):
    """
    Print a message to the console.
    """
    if not DEBUG_MODE:
        return

    timestamp = datetime.now().strftime("%Y-%b-%d %H:%M:%S")
    prefix = f"{timestamp}: swpwrxblock"
    LoggerBuffer().log(prefix + " - " + msg)
    print(prefix + " - " + msg)


def validate_path(path):
    """
    Check if a path exists, and raise an exception if it does not.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"copy_assets() path not found: {path}")
    logger("validate_path() validated: " + path)


def verify_path(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"verify_path() path not found: {path}")


def get_install_path():
    """
    Get the file system installation path of this package.
    """
    dist = pkg_resources.get_distribution(PACKAGE_NAME)
    install_path = os.path.join(dist.location, "swpwrxblock")
    verify_path(install_path)

    logger(f"post_install.get_install_path() - installation path: {install_path}")
    return install_path
