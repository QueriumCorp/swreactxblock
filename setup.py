# -*- coding: utf-8 -*-
"""
pip installation configuration for the Stepwise Power XBlock.
"""
import importlib
import sys

import pkg_resources
from setuptools import find_packages, setup
from setuptools.command.install import install

PACKAGE_NAME = "stepwise-power-xblock"


class PostInstallCommand(install):
    """
    Post-installation for installation mode.

    IMPORTANT: This class is used to compile the
    static assets of the **INSTALLED** package, noting that this setup.py
    module is executed from wherever the repo was cloned. Since these are
    two distinct location on the file system, we need to use pkg_resources
    to locate the installed package and import the copy_assets function from
    the installed package rather than from wherever setup() itself was
    invoked.
    """

    def run(self):
        # Run the standard installation process
        install.run(self)

        # Get the distribution object for the installed package
        dist = pkg_resources.get_distribution(PACKAGE_NAME)

        # Determine the installation path
        install_path = dist.location
        print("PostInstallCommand.run() - installation path: {}".format(install_path))

        # Add the installation path to sys.path to ensure the module can be imported
        if install_path not in sys.path:
            sys.path.append(install_path)
            print(
                "PostInstallCommand.run() - appending to system path: {}".format(
                    install_path
                )
            )

        # Import the copy_assets function from the installed package
        module_name = "swpwrxblock.post_install"
        module = importlib.import_module(module_name)
        copy_assets = getattr(module, "copy_assets")

        # Execute the copy_assets function
        copy_assets()


setup(
    name=PACKAGE_NAME,
    version="18.1.1",
    description="Stepwise Power XBlock",
    license="MIT",
    install_requires=["XBlock", "requests"],
    packages=find_packages(where="."),
    package_data={"swpwrxblock": ["static/**", "public/**", "translations/**"]},
    entry_points={"xblock.v1": ["swpwrxblock = swpwrxblock:SWPWRXBlock"]},
    cmdclass={
        "install": PostInstallCommand,
    },
)
