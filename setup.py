# Pylint: disable=W0718,W0611,W1203
"""Setup for swpwrxblock XBlock."""

import os
import glob
import logging
from setuptools import setup, Command


# our stuff
from version import VERSION
from install_swpwr import copy_assets

logger = logging.getLogger(__name__)

# Read the ENVIRONMENT_ID environment variable
environment_id = os.environ.get("ENVIRONMENT_ID", "prod")
print(f"ENVIRONMENT_ID: {environment_id}")


class RunScript(Command):
    """
    Automate populating the public/ folder with the latest React build assets for the swpwr react app.
    """

    description = "Run a custom bash script"
    user_options = []

    def __init__(self, dist, **kw):
        super().__init__(dist, **kw)
        self.environment_id = environment_id

    def clean_public(self):
        """
        ensure that the public/ folder is empty except for README.md
        at the point in time that we run this script
        """
        public_dir = "../swpwrxblock/public"
        files = glob.glob(os.path.join(public_dir, "*"))

        for file in files:
            if os.path.isfile(file) and not file.endswith("README.md"):
                os.remove(file)
                logger.warning(f"Deleted: {file}")

    def initialize_options(self):
        """
        delete anything in swpwrxblock/public except for README.md
        """
        self.clean_public()

    def finalize_options(self):
        """Finalize tasks."""
        pass

    def run(self):
        """
        Do setup() tasks.
        """
        copy_assets(self.environment_id)


def package_data(pkg, roots):
    """Generic function to find package_data.

    All of the files under each of the `roots` will be declared as package
    data for package `pkg`.

    """
    data = []
    for root in roots:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}


setup(
    name="swpwrxblock-xblock",
    version=VERSION,
    description="swpwrxblock XBlock",
    license="MIT",
    packages=[
        "swpwrxblock",
    ],
    install_requires=[
        "XBlock",
    ],
    entry_points={
        "xblock.v1": [
            "swpwrxblock = swpwrxblock:SWPWRXBlock",
        ]
    },
    package_data=package_data(
        "swpwrxblock",
        ["static", "public", "translations"],
    ),
    include_package_data=True,
    cmdclass={
        "run_script": RunScript,
    },
)
