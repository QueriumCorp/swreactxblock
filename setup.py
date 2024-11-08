# -*- coding: utf-8 -*-
# Pylint: disable=W0718,W0611,W1203
"""Setup for swpwrxblock XBlock."""

import glob

# python stuff
import os
import re
import shutil
import tarfile

from setuptools import setup

# our stuff
from version import VERSION

HERE = os.path.abspath(os.path.dirname(__file__))
ENVIRONMENT_ID = os.environ.get("ENVIRONMENT_ID", "prod")


def logger(msg: str):
    """
    Print a message to the console.
    """
    prefix = "stepwise-power-xblock"
    print(prefix + ": " + msg)


logger(f"ENVIRONMENT_ID: {ENVIRONMENT_ID}")


def validate_path(path):
    """
    Check if a path exists, and raise an exception if it does not.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"copy_assets() path not found: {path}")
    logger("copy_assets() validated path: " + path)


def clean_public():
    """
    ensure that the public/ folder is empty except for README.md
    at the point in time that we run this script
    """
    public_dir = os.path.join(HERE, "swpwrxblock", "public")
    logger(f"clean_public() cleaning {public_dir}")
    files = glob.glob(os.path.join(public_dir, "*"))

    for file in files:
        if os.path.isfile(file) and not file.endswith("README.md"):
            os.remove(file)
            logger(f"clean_public() deleted: {file}")


def fix_css_url(css_filename):
    """
    fix any CSS asset file reference to point at the swpwrxblock static assets directory
    """
    logger(f"fix_css_url() {css_filename}")
    if not css_filename:
        raise ValueError("fix_css_url() no value received for css_filename.")

    css_file_path = os.path.join(HERE, "public", "dist", "assets", css_filename)
    if not os.path.isfile(css_file_path):
        raise FileNotFoundError(f"fix_css_url() file not found: {css_file_path}")

    with open(css_file_path, "r", encoding="utf-8") as file:
        data = file.read()

    data = data.replace(
        "url(/swpwr/assets", "url(/static/xblock/resources/swpwrxblock/public/assets"
    )

    with open(css_file_path, "w", encoding="utf-8") as file:
        file.write(data)

    logger(f"updated CSS file {css_file_path}")


def fix_js_url(js_filename):
    """
    fix any JS asset file references to the foxy.glb 3D model to point at the swpwrxblock static assets directory
    """
    logger(f"fix_js_url() {js_filename}")
    if not js_filename:
        raise ValueError("fix_js_url() no value received for js_filename.")

    js_file_path = os.path.join(HERE, "public", "dist", "assets", js_filename)
    if not os.path.isfile(js_file_path):
        raise FileNotFoundError(f"fix_js_url() file not found: {js_file_path}")

    with open(js_file_path, "r", encoding="utf-8") as file:
        data = file.read()

    # foxy.glb lives in dist/models
    data = data.replace(
        '"/swpwr/models/foxy.glb"',
        '"/static/xblock/resources/swpwrxblock/public/dist/models/foxy.glb"',
    )

    with open(js_file_path, "w", encoding="utf-8") as file:
        file.write(data)

    logger(f"updated JavaScript file {js_file_path}")


def copy_assets(environment="prod"):
    """
    Download and position ReactJS build assets in the appropriate directories.
    (A) creates the public folder in our build directory,
    (B) copies all of the public/ contents from the swpwr react assets,
    (C) Displays the 2 lings of HTML that need to replace what is in
        static/html/swpwrxstudent.html, and
    (D) displays what commands to run as fixcsurl.sh and fixjsurl.sh to add the
        right hash string to fix the asset paths that are referenced by other assets.
    """
    logger("copy_assets() starting swpwr installation script")
    import requests

    # Set the environment based CDN URL
    domain = {
        "dev": "cdn.dev.stepwisemath.ai",
        "prod": "cdn.web.stepwisemath.ai",
        "staging": "cdn.staging.stepwisemath.ai",
    }.get(environment, None)

    if domain is None:
        raise ValueError(f"copy_assets() Invalid environment: {environment}")

    logger(f"downloading ReactJS build assets from {domain}")

    # Full pathnames to the swpwr build and public directories
    i = os.path.join(HERE, "public")
    d = os.path.join(i, "dist")
    b = os.path.join(d, "assets")

    # Create necessary directories if they do not exist
    os.makedirs(i, exist_ok=True)
    os.makedirs(d, exist_ok=True)
    os.makedirs(b, exist_ok=True)

    # Read VERSION from the CDN and extract the semantic version of the latest release
    version_url = f"https://{domain}/swpwr/VERSION"
    logger(f"copy_assets() retrieving swpwr package version from {version_url}")
    response = requests.get(version_url)
    version = "Unknown"
    if response.status_code == 200:
        version = response.text.strip()
    else:
        response.raise_for_status()

    # validate that the version is a semantic version. example: v1.2.300
    if not re.match(r"^v[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}$", version):
        raise ValueError(f"copy_assets() invalid version: {version} from {version_url}")

    logger(f"copy_assets() latest swpwr version is {version}")

    # Download the latest swpwr release tarball
    tarball_filename = f"swpwr-{version}.tar.gz"
    tarball_url = f"https://{domain}/swpwr/{tarball_filename}"
    logger(f"copy_assets() downloading {tarball_url}")
    with requests.get(tarball_url, stream=True) as r:
        with open(tarball_filename, "wb") as f:
            shutil.copyfileobj(r.raw, f)
        logger(f"copy_assets() successfully downloaded {tarball_filename}")

    # Extract the tarball and move the contents to swpwrxblock's public directory
    logger(f"copy_assets() extracting {tarball_filename}")
    with tarfile.open(tarball_filename, "r:gz") as tar:
        tar.extractall(path=i)

    # validate the extracted tarball contents
    validate_path(d)
    for folder_path in [
        "assets",
        "BabyFox",
        "models",
    ]:
        validate_path(os.path.join(d, folder_path))
    # validate a couple of sample contents files that should be in public/dist
    validate_path(os.path.join(d, "index.html"))
    validate_path(os.path.join(d, "sadPanda.svg"))

    # Get the names of the most recent index-<hash>.js and index-<hash>.css files
    logger(
        "copy_assets() determining the most recent index.js and index.css file hashes"
    )
    js1 = max(
        [f for f in os.listdir(b) if f.startswith("index") and f.endswith(".js")],
        key=lambda x: os.path.getmtime(os.path.join(b, x)),
    )
    cs1 = max(
        [f for f in os.listdir(b) if f.startswith("index") and f.endswith(".css")],
        key=lambda x: os.path.getmtime(os.path.join(b, x)),
    )

    # Remember swpwr version info in a jsonf ile in public/dist/assets
    logger("copy_assets() re-writing swpwr_version.json")
    with open(os.path.join(b, "swpwr_version.json"), "w", encoding="utf-8") as f:
        f.write(f'{{"version": "{version}"}}')

    # change the bugfender.com API version tag in swpwrxblock.py
    with open("swpwrxblock/swpwrxblock.py", "r", encoding="utf-8") as file:
        data = file.read().replace(
            "dashboard.bugfender.com/\\', version: \\'v?[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}",
            f"dashboard.bugfender.com/\\', version: \\'{version}",
        )

    logger("copy_assets() re-writing swpwrxblock/swpwrxblock.py")
    with open("swpwrxblock/swpwrxblock.py", "w", encoding="utf-8") as file:
        file.write(data)

    logger(f"copy_assets() We are incorporating swpwr {version}")
    logger(f"copy_assets() The top-level Javascript file is {js1}")
    logger(f"copy_assets() The top-level CSS file is {cs1}")

    fix_css_url(css_filename=cs1)
    fix_js_url(js_filename=js1)

    # Update the xblock student view HTML file with the new JS and CSS filenames
    swpwrxstudent_html_path = os.path.join(
        HERE, "swpwrxblock", "static", "html", "swpwrxstudent.html"
    )
    logger(f"Updating {swpwrxstudent_html_path}")

    with open(swpwrxstudent_html_path, "r", encoding="utf-8") as file:
        data = file.read()
    # handle the case where the JS path has public to make it have react_build/dist/assets
    data = data.replace(
        '<script type="module" crossorigin src="/static/xblock/resources/swpwrxblock/public.*$',
        f'<script type="module" crossorigin src="/static/xblock/resources/swpwrxblock/public/dist/assets/{js1}"></script>',
    )
    # handle the case where the CSS path has public to make it have react_build/dist/assets
    data = data.replace(
        '<link rel="module" crossorigin href="/static/xblock/resources/swpwrxblock/public.*$',
        f'<link rel="stylesheet" crossorigin href="/static/xblock/resources/swpwrxblock/public/dist/assets/{cs1}">',
    )
    # now write out the updated MHTL student view file
    with open(swpwrxstudent_html_path, "w", encoding="utf-8") as file:
        file.write(data)

    logger(f"copy_assets() Updated {swpwrxstudent_html_path}")
    logger("copy_assets() finished running swpwr installation script")


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
    name="stepwise-power-xblock",
    version=VERSION,
    description="Stepwise Power XBlock",
    license="MIT",
    packages=[
        "swpwrxblock",
    ],
    install_requires=["XBlock"],
    setup_requires=["requests"],
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
)
clean_public()
copy_assets(ENVIRONMENT_ID)
