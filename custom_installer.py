# -*- coding: utf-8 -*-
# pylint: disable=W1201
"""
pip installation configuration for the Stepwise Power XBlock.
"""

# python stuff
import importlib
import logging
import os
import platform
import sys

# 3rd party stuff
from setuptools.command.install import install as _install

PACKAGE_NAME = "stepwise-power-xblock"

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.info("custom_installer.py - Imported")


class CustomInstall(_install):
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

        Note: upon entering this method, the package has been
        a.) cloned from the github repo
        b.) built by wheel, and is now ready to be built into a bdist by wheel
        """
        logger.info(PACKAGE_NAME + " CustomInstall().run() - Starting")
        # Ensure the normal setup() has completed all operations
        self.execute(
            self.swpwrxblock_post_installation, (), msg="Running post install task"
        )

        # copies build to bdist directory in the wheel temporary directory
        super().run()
        logger.info(PACKAGE_NAME + " CustomInstall().run() - Completed")

    ###########################################################################
    # private post-installation task methods
    ###########################################################################
    def _verify_path(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"verify_path() path not found: {path}")

    def _get_build_path(self):
        """
        Get the wheel build path of this package. this is expected to be
        inside the temporary directory of the wheel build process.
        """
        relative_path = os.path.join(self.build_lib, "swpwrxblock")
        build_path = os.path.abspath(relative_path)
        self._verify_path(build_path)
        logger.info(
            PACKAGE_NAME + " CustomInstall()._get_build_path(): %s",
            build_path,
        )
        return build_path

    def _get_bdist_path(self):
        """
        Get the file system pip wheel bdist path for this package.
        mcdaniel: Can this be removed?
        """
        relative_path = self.install_lib
        bdist_path = os.path.abspath(relative_path)
        self._verify_path(bdist_path)
        logger.info(
            PACKAGE_NAME + " CustomInstall()._get_bdist_path(): %s",
            bdist_path,
        )
        return bdist_path

    def _set_path(self, build_path):
        """
        Append the installation path to the system path in order to ensure that
        python can find the installed package, and that it can import modules
        from the installed package.
        """
        if build_path not in sys.path:
            sys.path.append(build_path)
            logger.info(
                PACKAGE_NAME
                + " CustomInstall()._set_path() - appending to system path: {}".format(
                    build_path
                )
            )

    def _write_diagnostics(self, build_path):
        """
        Write diagnostic information to a file in the current working directory.
        """
        diagnostic_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "installation_path": build_path,
            "sys_path": sys.path,
            "current_working_directory": os.getcwd(),
        }

        diagnostic_file_path = os.path.join(build_path, "setup_diagnostic_info.out")
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
        logger.info(
            PACKAGE_NAME + " CustomInstall().swpwrxblock_post_installation() - Starting"
        )
        build_path = self._get_build_path()
        self._set_path(build_path)
        self._write_diagnostics(build_path)

        module_name = "swpwrxblock.post_install"
        module = importlib.import_module(module_name)
        copy_assets = getattr(module, "copy_assets")
        copy_assets(build_path=build_path, bdist_path="")
        logger.info(
            PACKAGE_NAME
            + " CustomInstall().swpwrxblock_post_installation() - completed"
        )
