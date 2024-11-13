# -*- coding: utf-8 -*-
"""
pip installation configuration for the Stepwise Power XBlock.
"""
import importlib
import logging
import os
import platform
import sys

import pkg_resources
from setuptools import find_packages, setup
from setuptools.command.install import install

PACKAGE_NAME = "stepwise-power-xblock"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CustomInstaller(install):
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
        """
        Override the default run() method, adding a post-install method
        that copies ReactJS build assets.
        """
        install.run(self)

        # Ensure the normal setup() has completed all operations
        self.execute(
            self.swpwrxblock_post_installation, (), msg="Running post install task"
        )

    ###########################################################################
    # private post-installation task methods
    ###########################################################################
    def _get_install_path(self):
        """
        Get the file system installation path of this package.
        """
        dist = pkg_resources.get_distribution(PACKAGE_NAME)
        install_path = dist.location
        logger.info(
            "CustomInstaller._get_install_path() - installation path: %s",
            install_path,
        )
        return install_path

    def _set_path(self, install_path):
        """
        Append the installation path to the system path in order to ensure that
        python can find the installed package, and that it can import modules
        from the installed package.
        """
        if install_path not in sys.path:
            sys.path.append(install_path)
            logger.info(
                "CustomInstaller._set_path() - appending to system path: {}".format(
                    install_path
                )
            )

    def _write_diagnostics(self, install_path):
        """
        Write diagnostic information to a file in the current working directory.
        """
        diagnostic_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "installation_path": install_path,
            "sys_path": sys.path,
            "current_working_directory": os.getcwd(),
        }

        diagnostic_file_path = os.path.join(os.getcwd(), "setup_diagnostic_info.out")
        with open(diagnostic_file_path, "w", encoding="utf-8") as diagnostic_file:
            for key, value in diagnostic_info.items():
                diagnostic_file.write(f"{key}: {value}\n")
            diagnostic_file.flush()
            os.fsync(diagnostic_file.fileno())

    ###########################################################################
    # top-level post-installation task method
    ###########################################################################
    def swpwrxblock_post_installation(self):
        """
        Post-installation task to copy assets into the installed package
        from the ReactJS build, stored in a remote CDN.
        """
        install_path = self._get_install_path()
        self._write_diagnostics(install_path)
        self._set_path(install_path)

        module_name = "swpwrxblock.post_install"
        module = importlib.import_module(module_name)
        copy_assets = getattr(module, "copy_assets")
        copy_assets()


setup(
    name=PACKAGE_NAME,
    version="18.1.6",
    description="Stepwise Power XBlock",
    license="MIT",
    install_requires=["XBlock", "requests"],
    packages=find_packages(where="."),
    package_data={
        "swpwrxblock": ["static/**", "public/**", "translations/**", "README.md"]
    },
    entry_points={"xblock.v1": ["swpwrxblock = swpwrxblock:SWPWRXBlock"]},
    cmdclass={
        "install": CustomInstaller,
    },
)
