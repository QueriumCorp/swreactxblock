# -*- coding: utf-8 -*-
"""
pip installation configuration for the Stepwise Power XBlock.
"""
# python stuff
import logging

# 3rd party stuff
from setuptools import find_packages, setup

# our stuff
from custom_installer import CustomInstall

PACKAGE_NAME = "stepwise-power-xblock"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


setup(
    name=PACKAGE_NAME,
    version="18.1.15",
    description="Stepwise Power XBlock",
    license="MIT",
    install_requires=["XBlock", "requests"],
    packages=find_packages(where="."),
    package_data={
        "swpwrxblock": ["static/**", "public/**", "translations/**", "README.md"]
    },
    entry_points={"xblock.v1": ["swpwrxblock = swpwrxblock:SWPWRXBlock"]},
    cmdclass={
        "install": CustomInstall,
    },
)
