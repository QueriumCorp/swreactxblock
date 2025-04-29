# -*- coding: utf-8 -*-
# Pylint: disable=W0718,W0611,W1203
"""
Setup for swreactxblock XBlock. Collects the ReactJS build assets originating
from https://github.com/QueriumCorp/swreact and stores these in
swreactxblock/public.
"""
# python stuff
import os
import re
import shutil
import tarfile

# our stuff
from .const import (
    DEFAULT_ENVIRONMENT,
    ENVIRONMENT_DEV,
    ENVIRONMENT_PROD,
    ENVIRONMENT_STAGING,
    HTTP_TIMEOUT,
    VALID_ENVIRONMENTS,
)
from .utils import logger, save_logs, validate_path

# The environment ID is used to determine which CDN to download the assets from.
# It is set as a bash environment variable in the openedx Dockerfile,
# itself managed by tutor plugin, https://github.com/StepwiseMath/tutor-contrib-stepwise-config
STEPWISEMATH_ENV = os.environ.get("STEPWISEMATH_ENV", DEFAULT_ENVIRONMENT)

if STEPWISEMATH_ENV not in VALID_ENVIRONMENTS:
    raise ValueError(
        f"Invalid value received for STEPWISEMATH_ENV: {STEPWISEMATH_ENV}. "
        f"Expected one of {VALID_ENVIRONMENTS}. "
        "Refer to https://github.com/StepwiseMath/tutor-contrib-stepwise-config "
        "and/or https://github.com/lpm0073/openedx_devops/tree/main/.github/workflows"
    )

logger("DEBUG: swreactxblock.post_install import successful")
logger(f"STEPWISEMATH_ENV: {STEPWISEMATH_ENV}")


def fix_css_url(css_filename: str, build_path: str):
    """
    fix any CSS asset file reference to point at the swreactxblock static assets directory
    """
    logger(f"fix_css_url() {css_filename}")
    if not css_filename:
        raise ValueError("fix_css_url() no value received for css_filename.")

    css_file_path = os.path.join(build_path, "public", "dist", "assets", css_filename)
    if not os.path.isfile(css_file_path):
        raise FileNotFoundError(f"fix_css_url() file not found: {css_file_path}")

    with open(css_file_path, "r", encoding="utf-8") as file:
        data = file.read()

    data = data.replace(
        "url(/swreact/assets", "url(/static/xblock/resources/swreactxblock/public/assets"
    )

    with open(css_file_path, "w", encoding="utf-8") as file:
        file.write(data)

    logger(f"updated CSS file {css_file_path}")


def copy_assets(build_path: str, bdist_path: str, environment: str = None):
    """
    Download and position ReactJS build assets in the appropriate directories.
    (A) creates the public/ folder in our build directory,
    (B) Untars all of the swreact dist contents into public/dist.
    """
    logger("copy_assets() starting swreact installation script", build_path=build_path)
    logger(f"copy_assets() build_path={build_path}")
    logger(f"copy_assets() bdist_path={bdist_path}")

    # pylint: disable=C0415
    import requests

    if not environment:
        environment = STEPWISEMATH_ENV

    # Set the environment based CDN URL
    domain = {
        ENVIRONMENT_DEV: "cdn.dev.stepwisemath.ai",
        ENVIRONMENT_STAGING: "cdn.staging.stepwisemath.ai",
        ENVIRONMENT_PROD: "cdn.web.stepwisemath.ai",
    }.get(environment, None)

    if domain is None:
        raise ValueError(f"copy_assets() Invalid environment: {environment}")

    logger(f"downloading ReactJS build assets from {domain}")

    # Full pathnames to the swreact build and public directories
    i = os.path.join(build_path, "public")
    d = os.path.join(i, "dist")
    b = os.path.join(d, "assets")

    # Create necessary directories if they do not exist
    os.makedirs(i, exist_ok=True)
    os.makedirs(d, exist_ok=True)
    os.makedirs(b, exist_ok=True)
    logger(f"copy_assets() i={i}")
    logger(f"copy_assets() d={d}")
    logger(f"copy_assets() b={b}")

    # Read VERSION from the CDN and extract the semantic version of the latest release
    version_url = f"https://{domain}/swreact/VERSION"
    logger(f"copy_assets() retrieving swreact package version from {version_url}")
    response = requests.get(version_url, timeout=HTTP_TIMEOUT)
    version = "Unknown"
    if response.status_code == 200:
        version = response.text.strip()
    else:
        response.raise_for_status()

    # validate that the version is a semantic version. example: v1.2.300
    if not re.match(r"^v[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}$", version):
        raise ValueError(f"copy_assets() invalid version: {version} from {version_url}")

    logger(f"copy_assets() latest swreact version is {version}")

    # Download the latest swreact release tarball
    tarball_filename = f"swreact-{version}.tar.gz"
    full_tarball_path = os.path.abspath(tarball_filename)
    tarball_url = f"https://{domain}/swreact/{tarball_filename}"
    logger(f"copy_assets() downloading {tarball_url} to {full_tarball_path}")
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
        os.remove(tarball_filename)

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

    validate_path(os.path.join(d, "BabyFox", "BabyFox.svg"))

    # we no longer validate paths with hashes in the filename so the code isn't tied to the filenames in the react app distribution
    # validate_path(os.path.join(d, "assets", "DailyMotion-Bb7kos7h.js"))
    # validate_path(os.path.join(d, "assets", "Facebook-DLhvQtLB.js"))
    # validate_path(os.path.join(d, "assets", "FilePlayer-CIfFZ4b8.js"))
    # validate_path(os.path.join(d, "assets", "KaTeX_AMS-Regular-BQhdFMY1.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_Caligraphic-Bold-Dq_IR9rO.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_Caligraphic-Regular-Di6jR-x-.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_Fraktur-Bold-CL6g_b3V.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_Fraktur-Regular-CTYiF6lA.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_Main-Bold-Cx986IdX.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_Main-BoldItalic-DxDJ3AOS.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_Main-Italic-NWA7e6Wa.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_Main-Regular-B22Nviop.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_Math-BoldItalic-CZnvNsCZ.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_Math-Italic-t53AETM-.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_SansSerif-Bold-D1sUS0GD.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_SansSerif-Italic-C3H0VqGB.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_SansSerif-Regular-DDBCnlJ7.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_Script-Regular-D3wIWfF6.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_Size1-Regular-mCD8mA8B.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_Size2-Regular-Dy4dx90m.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_Size4-Regular-Dl5lxZxV.woff2"))
    # validate_path(os.path.join(d, "assets", "KaTeX_Typewriter-Regular-CO6r4hn1.woff2"))
    # validate_path(os.path.join(d, "assets", "Kaltura-Do9z9Dhq.js"))
    # validate_path(os.path.join(d, "assets", "Mixcloud-xxYATmwO.js"))
    # validate_path(os.path.join(d, "assets", "Mux-C777p6u5.js"))
    # validate_path(os.path.join(d, "assets", "Preview-D76yD220.js"))
    # validate_path(os.path.join(d, "assets", "SoundCloud-V2Z7FnWf.js"))
    # validate_path(os.path.join(d, "assets", "Streamable-BRrsjUGO.js"))
    # validate_path(os.path.join(d, "assets", "Twitch-BM4Su8GF.js"))
    # validate_path(os.path.join(d, "assets", "Vidyard-CGoH-OJj.js"))
    # validate_path(os.path.join(d, "assets", "Vimeo-C6QJtfs2.js"))
    # validate_path(os.path.join(d, "assets", "Wistia-Ah2BW4ms.js"))
    # validate_path(os.path.join(d, "assets", "YouTube-rlL1waAH.js"))
    # validate_path(os.path.join(d, "assets", "index-B_VqGgJi.css"))
    # validate_path(os.path.join(d, "assets", "index-BdxI-PSa.js"))

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

    # Remember swreact version info in a jsonf ile in public/dist/assets
    logger("copy_assets() re-writing swreact_version.json")
    with open(os.path.join(b, "swreact_version.json"), "w", encoding="utf-8") as f:
        f.write(f'{{"version": "{version}"}}')
    logger(f"copy_assets() swreact_version.json is now set for {version}")

    # change the bugfender.com API version tag in swreactxblock.py
    with open("swreactxblock/swreactxblock.py", "r", encoding="utf-8") as file:
        data = file.read().replace(
            "dashboard.bugfender.com/\\', version: \\'v?[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}",
            f"dashboard.bugfender.com/\\', version: \\'{version}",
        )

    logger("copy_assets() re-writing swreactxblock/swreactxblock.py")
    with open("swreactxblock/swreactxblock.py", "w", encoding="utf-8") as file:
        file.write(data)

    logger(f"copy_assets() We are incorporating swreact {version}")
    logger(f"copy_assets() The top-level Javascript file is {js1}")
    logger(f"copy_assets() The top-level CSS file is {cs1}")

    fix_css_url(css_filename=cs1, build_path=build_path)

    # Update the xblock student view HTML file with the new JS and CSS filenames
    swreactxstudent_html_path = os.path.join(
        build_path, "static", "html", "swreactxstudent.html"
    )
    logger(f"Updating {swreactxstudent_html_path}")

    with open(swreactxstudent_html_path, "r", encoding="utf-8") as file:
        data = file.read()
    logger(
        f"copy_assets() Before replace with js1={js1} and cs1={cs1} in student view, data is:\n{data}"
    )
    # handle the legacy case where the JS path has public/ to make it have public/dist/assets/
    # Note that the path snippet 'dist/' was optional for backward compatibility
    data = re.sub(
        r'<script type="module" crossorigin src="/static/xblock/resources/swreactxblock/public.*"></script>$',
        f'<script type="module" crossorigin src="/static/xblock/resources/swreactxblock/public/dist/assets/{js1}"></script>',
        data,
        flags=re.MULTILINE
    )
    # handle the legacy case where the CSS path has public/ to make it have public/dist/assets/
    data = re.sub(
        r'<link rel="stylesheet" crossorigin href="/static/xblock/resources/swreactxblock/public.*">$',
        f'<link rel="stylesheet" crossorigin href="/static/xblock/resources/swreactxblock/public/dist/assets/{cs1}">',
        data,
        flags=re.MULTILINE
    )
    logger(
        f"copy_assets() After replace with js1={js1} and cs1={cs1} in student view, data is:\n{data}"
    )

    # now write out the updated MHTL student view file
    with open(swreactxstudent_html_path, "w", encoding="utf-8") as file:
        file.write(data)

    logger(f"copy_assets() Updated {swreactxstudent_html_path}")
    logger("copy_assets() finished running swreact installation script")

    # normally pip won't display our logger output unless there is an error, so
    # force an error at the end of setup() so we can review this output
    # validate_path(os.path.join(d, "models", "iDontExist.tsx"))
    save_logs()
