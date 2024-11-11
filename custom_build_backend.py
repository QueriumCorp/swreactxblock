# -*- coding: utf-8 -*-
"""
for pyproject.toml
"""
import os
import sys
from importlib import import_module

# Set the PYTHONPATH based on the relative location of this script
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import and call the actual build backend
backend = import_module("install.build_backend")
CustomBuildBackend = backend.CustomBuildBackend


# Expose the necessary functions for the build backend
def get_requires_for_build_wheel(config_settings=None):
    return CustomBuildBackend().get_requires_for_build_wheel(config_settings)


def get_requires_for_build_sdist(config_settings=None):
    return CustomBuildBackend().get_requires_for_build_sdist(config_settings)


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    return CustomBuildBackend().prepare_metadata_for_build_wheel(
        metadata_directory, config_settings
    )


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    return CustomBuildBackend().build_wheel(
        wheel_directory, config_settings, metadata_directory
    )


def build_sdist(sdist_directory, config_settings=None):
    return CustomBuildBackend().build_sdist(sdist_directory, config_settings)
