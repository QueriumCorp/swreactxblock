# -*- coding: utf-8 -*-
# pylint: disable=C0415,C0115,missing-function-docstring
"""
Custom build backend for setuptools to copy assets before building the package.
"""

import sys

print("DEBUG: custom_build_backend.backend import successful")
print("DEBUG: sys.path =", sys.path)


class CustomBuildBackend:
    """
    Custom build backend for setuptools to copy assets before building the package.
    """

    def build_wheel(
        self, wheel_directory, config_settings=None, metadata_directory=None
    ):
        print("DEBUG: CustomBuildBackend.build_wheel() called")
        self._copy_assets()
        return self._build_wheel(wheel_directory, config_settings, metadata_directory)

    def get_requires_for_build_wheel(self, config_settings=None):
        print("DEBUG: CustomBuildBackend.get_requires_for_build_wheel() called")
        return []

    def get_requires_for_build_sdist(self, config_settings=None):
        print("DEBUG: CustomBuildBackend.get_requires_for_build_sdist() called")
        return []

    def prepare_metadata_for_build_wheel(
        self, metadata_directory, config_settings=None
    ):
        print("DEBUG: CustomBuildBackend.prepare_metadata_for_build_wheel() called")
        self._copy_assets()
        return self._prepare_metadata_for_build_wheel(
            metadata_directory, config_settings
        )

    def _copy_assets(self):
        from custom_build_backend.collect_reactapp import copy_assets

        print("DEBUG: Copying assets")
        copy_assets()

    def _build_wheel(
        self, wheel_directory, config_settings=None, metadata_directory=None
    ):
        from setuptools import build_meta

        return build_meta.build_wheel(
            wheel_directory, config_settings, metadata_directory
        )

    def _prepare_metadata_for_build_wheel(
        self, metadata_directory, config_settings=None
    ):
        from setuptools import build_meta

        return build_meta.prepare_metadata_for_build_wheel(
            metadata_directory, config_settings
        )


# Expose the backend class
def get_requires_for_build_wheel(config_settings=None):
    print("DEBUG: get_requires_for_build_wheel() called")
    return []


def get_requires_for_build_sdist(config_settings=None):
    print("DEBUG: get_requires_for_build_sdist() called")
    return []


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    print("DEBUG: prepare_metadata_for_build_wheel() called")
    backend = get_backend()
    return backend.prepare_metadata_for_build_wheel(metadata_directory, config_settings)


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    print("DEBUG: build_wheel() called")
    backend = get_backend()
    return backend.build_wheel(wheel_directory, config_settings, metadata_directory)


def get_backend():
    print("DEBUG: get_backend() called")
    return CustomBuildBackend()
