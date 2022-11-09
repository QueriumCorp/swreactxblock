"""Setup for swpwrxblock XBlock."""

import os

from setuptools import setup


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
    name='swpwrxblock-xblock',
    version='1.5.0',
    description='swpwrxblock XBlock',   # TODO: write a better description.
    license='UNKNOWN',          # TODO: choose a license: 'AGPL v3' and 'Apache 2.0' are popular.
    packages=[
        'swpwrxblock',
    ],
    install_requires=[
        'XBlock',
    ],
    entry_points={
        'xblock.v1': [
            'swpwrxblock = swpwrxblock:SWPWRXBlock',
        ]
    },
    package_data=package_data("swpwrxblock", ["swpwrxblock/static/media","swpwrxblock/static","static", "public", "public/assets", "public/assets/js", "public/assets/css", "static/media", "media"]),
    include_package_data=True,
)
