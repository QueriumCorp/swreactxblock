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
HTTP_TIMEOUT = 30


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


def copy_assets(environment="prod"):
    """
    Download and position ReactJS build assets in the appropriate directories.
    (A) creates the public/ folder in our build directory,
    (B) Untars all of the swpwr dist contents into public/dist.
    """
    logger("copy_assets() starting swpwr installation script")

    # pylint: disable=C0415
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
    response = requests.get(version_url, timeout=HTTP_TIMEOUT)
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
    with requests.get(tarball_url, stream=True, timeout=HTTP_TIMEOUT) as r:
        with open(tarball_filename, "wb") as f:
            shutil.copyfileobj(r.raw, f)
        logger(f"copy_assets() successfully downloaded {tarball_filename}")

    def is_within_directory(directory, target):
        """
        Check if the target path is within the given directory.
        """
        abs_directory = os.path.abspath(directory)
        abs_target = os.path.abspath(target)
        return os.path.commonpath([abs_directory]) == os.path.commonpath(
            [abs_directory, abs_target]
        )

    def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        """
        Safely extract tar file members to avoid path traversal attacks.
        """
        for member in tar.getmembers():
            member_path = os.path.join(path, member.name)
            if not is_within_directory(path, member_path):
                raise tarfile.TarError("Attempted Path Traversal in Tar File")
        # Extract the tarball contents. This is safe because we have already
        # validated the paths, hence the `nosec` comment.
        tar.extractall(path, members, numeric_owner=numeric_owner)  # nosec

    logger(f"copy_assets() extracting {tarball_filename}")
    with tarfile.open(tarball_filename, "r:gz") as tar:
        safe_extract(tar, path=i)

    # validate the extracted tarball contents
    validate_path(d)
    for folder_path in [
        "assets",
        "BabyFox",
        "models",
    ]:
        validate_path(os.path.join(d, folder_path))

    # validate contents contents files that should be in public/dist
    validate_path(os.path.join(d, "BabyFox.svg"))
    validate_path(os.path.join(d, "android-chrome-192x192.png"))
    validate_path(os.path.join(d, "android-chrome-512x512.png"))
    validate_path(os.path.join(d, "apple-touch-icon.png"))
    validate_path(os.path.join(d, "favicon-16x16.png"))
    validate_path(os.path.join(d, "favicon-32x32.png"))
    validate_path(os.path.join(d, "favicon.ico"))
    validate_path(os.path.join(d, "index.html"))
    validate_path(os.path.join(d, "sadPanda.svg"))
    validate_path(os.path.join(d, "site.webmanifest"))
    validate_path(os.path.join(d, "stats.html"))
    validate_path(os.path.join(d, "vite.svg"))

    validate_path(os.path.join(d, "BabyFox", "BabyFox.svg"))

    validate_path(os.path.join(d, "assets", "DailyMotion-Bb7kos7h.js"))
    validate_path(os.path.join(d, "assets", "Facebook-DLhvQtLB.js"))
    validate_path(os.path.join(d, "assets", "FilePlayer-CIfFZ4b8.js"))
    validate_path(os.path.join(d, "assets", "KaTeX_AMS-Regular-BQhdFMY1.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_Caligraphic-Bold-Dq_IR9rO.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_Caligraphic-Regular-Di6jR-x-.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_Fraktur-Bold-CL6g_b3V.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_Fraktur-Regular-CTYiF6lA.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_Main-Bold-Cx986IdX.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_Main-BoldItalic-DxDJ3AOS.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_Main-Italic-NWA7e6Wa.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_Main-Regular-B22Nviop.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_Math-BoldItalic-CZnvNsCZ.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_Math-Italic-t53AETM-.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_SansSerif-Bold-D1sUS0GD.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_SansSerif-Italic-C3H0VqGB.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_SansSerif-Regular-DDBCnlJ7.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_Script-Regular-D3wIWfF6.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_Size1-Regular-mCD8mA8B.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_Size2-Regular-Dy4dx90m.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_Size4-Regular-Dl5lxZxV.woff2"))
    validate_path(os.path.join(d, "assets", "KaTeX_Typewriter-Regular-CO6r4hn1.woff2"))
    validate_path(os.path.join(d, "assets", "Kaltura-Do9z9Dhq.js"))
    validate_path(os.path.join(d, "assets", "Mixcloud-xxYATmwO.js"))
    validate_path(os.path.join(d, "assets", "Mux-C777p6u5.js"))
    validate_path(os.path.join(d, "assets", "Preview-D76yD220.js"))
    validate_path(os.path.join(d, "assets", "SoundCloud-V2Z7FnWf.js"))
    validate_path(os.path.join(d, "assets", "Streamable-BRrsjUGO.js"))
    validate_path(os.path.join(d, "assets", "Twitch-BM4Su8GF.js"))
    validate_path(os.path.join(d, "assets", "Vidyard-CGoH-OJj.js"))
    validate_path(os.path.join(d, "assets", "Vimeo-C6QJtfs2.js"))
    validate_path(os.path.join(d, "assets", "Wistia-Ah2BW4ms.js"))
    validate_path(os.path.join(d, "assets", "YouTube-rlL1waAH.js"))
    validate_path(os.path.join(d, "assets", "index-B_VqGgJi.css"))
    validate_path(os.path.join(d, "assets", "index-BdxI-PSa.js"))

    validate_path(os.path.join(d, "models", "FoxyFuka.glb"))
    validate_path(os.path.join(d, "models", "foxy-compressed.glb"))
    validate_path(os.path.join(d, "models", "foxy-uncompressed.glb"))
    validate_path(os.path.join(d, "models", "foxy.glb"))
    validate_path(os.path.join(d, "models", "newFoxy.tsx"))

    # Get the names of the most recent index-<hash>.js and index-<hash>.css files
    logger(
        "copy_assets() determining the most recent index.js and index.css file hashes"
    )
    js1 = max(
        (f for f in os.listdir(b) if f.startswith("index") and f.endswith(".js")),
        key=lambda x: os.path.getmtime(os.path.join(b, x)),
    )
    cs1 = max(
        (f for f in os.listdir(b) if f.startswith("index") and f.endswith(".css")),
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

    # normally pip won't display our logger output unless there is an error, so
    # force an error at the end of setup() so we can review this output
    # validate_path(os.path.join(d, "models", "iDontExist.tsx"))

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
copy_assets(ENVIRONMENT_ID)
