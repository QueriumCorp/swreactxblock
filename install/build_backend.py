# -*- coding: utf-8 -*-
# custom_build_backend.py
"""
Custom build backend for setuptools to copy assets before building the package.
"""

import subprocess

from setuptools.build_meta import build_sdist, build_wheel


def copy_assets():
    """
    subprocess driver to copy assets from the reactapp directory to
    the python package.
    """
    subprocess.check_call(["python", "install/collect_reactapp.py"])


class CustomBuildBackend:
    """
    Custom build backend for setuptools to copy assets before building the package.
    """

    def build_sdist(self, sdist_directory, config_settings=None):
        copy_assets()
        return build_sdist(sdist_directory, config_settings)

    def build_wheel(
        self, wheel_directory, config_settings=None, metadata_directory=None
    ):
        copy_assets()
        return build_wheel(wheel_directory, config_settings, metadata_directory)
