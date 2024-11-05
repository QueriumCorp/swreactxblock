# Pylint: disable=W0718,W0611
"""Setup for swpwrxblock XBlock."""

import os
import subprocess
from setuptools import setup, Command

# our stuff
import swpwrxblock

# Read the ENVIRONMENT_ID environment variable
environment_id = os.environ.get('ENVIRONMENT_ID', 'prod')
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
        
    def initialize_options(self):
        """
        delete anything in swpwrxblock/public except for README.md
        """
        try:
            subprocess.check_call(["bash", "scripts/cleanpublic.sh"])
        except Exception as e:
            print(e)

    def finalize_options(self):
        """Finalize tasks."""
        pass

    def run(self):
        """
        run cpassets.sh (run from updateme1.sh), which does 
            (A) creates the public folder in our build directory, 
            (B) copies all of the public/ contents from the swpwr react assets, 
            (C) Displays the 2 lings of HTML that need to replace what is in static/html/swpwrxstudent.html, and 
            (D) displays what comands to run as fixcsurl.sh and fixjsurl.sh to add the right hash string to fix the asset paths that are referenced by other assets.
        """

        try:
            cpassets = os.path.join(os.path.dirname(__file__), "scripts", "cpassets.sh")
            subprocess.check_call(["bash", cpassets, environment_id])
        except Exception as e:
            print(e)



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
    version=swpwrxblock.VERSION,
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
        [
            "static",
            "public",
        ],
    ),
    include_package_data=True,
    cmdclass={
        "run_script": RunScript,
    },
)
