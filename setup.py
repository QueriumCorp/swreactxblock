# Pylint: disable=W0718,W0611,W1203
"""Setup for swpwrxblock XBlock."""

# python stuff
import os
import glob
import re
import tarfile
import shutil
from setuptools import setup, Command


# our stuff
from version import VERSION

HERE = os.path.abspath(os.path.dirname(__file__))
ENVIRONMENT_ID = os.environ.get("ENVIRONMENT_ID", "prod")


def logger(msg: str):
    """
    Print a message to the console.
    """
    prefix = "swpwrxblock-xblock"
    print(prefix + ": " + msg)


logger(f"ENVIRONMENT_ID: {ENVIRONMENT_ID}")


class RunScript(Command):
    """
    Automate populating the public/ folder with the latest React build 
    assets for the swpwr react app.
    """

    description = "Run a custom bash script"
    user_options = []

    def __init__(self, dist, **kw):
        super().__init__(dist, **kw)
        self.ENVIRONMENT_ID = ENVIRONMENT_ID

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
                logger(f"Deleted: {file}")

    def initialize_options(self):
        """
        delete anything in swpwrxblock/public except for README.md
        """
        logger("Cleaning public/ directory")
        self.clean_public()

    def finalize_options(self):
        """Finalize tasks."""
        logger("Finalizing swpwr installation script")

    def run(self):
        """
        Do setup() tasks.
        """
        logger("Running swpwr installation script")
        copy_assets(self.ENVIRONMENT_ID)


def fix_css_url(css_filename):
    """
    what is this?
    """
    if not css_filename:
        raise ValueError("fix_css_url() no value received for css_filename.")

    css_file_path = os.path.join(HERE + "swpwrxblock", "public", css_filename)
    if not os.path.isfile(css_file_path):
        raise FileNotFoundError(f"fix_css_url() file not found: {css_file_path}")

    with open(css_file_path, "r", encoding="utf-8") as file:
        data = file.read()

    data = data.replace("url(/swpwr/assets", "url(/static/xblock/resources/swpwrxblock/public/assets")

    with open(css_file_path, "w", encoding="utf-8") as file:
        file.write(data)

    logger(f"updated CSS file {css_file_path}")


def fix_js_url(js_filename):
    """
    what is this?
    """
    if not js_filename:
        raise ValueError("fix_js_url() no value received for js_filename.")

    js_file_path = os.path.join(HERE, "swpwrxblock", "public", js_filename)
    if not os.path.isfile(js_file_path):
        raise FileNotFoundError(f"fix_js_url() file not found: {js_file_path}")

    with open(js_file_path, "r", encoding="utf-8") as file:
        data = file.read()

    data = data.replace('"/swpwr/models/foxy.glb"', '"/static/xblock/resources/swpwrxblock/public/models/foxy.glb"')

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
    (D) displays what comands to run as fixcsurl.sh and fixjsurl.sh to add the
        right hash string to fix the asset paths that are referenced by other assets.
    """
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
    i = os.path.join(HERE, "react_build")
    d = os.path.join(i, "dist")
    b = os.path.join(d, "assets")
    p = os.path.join(HERE, "swpwrxblock", "public")

    # Create necessary directories if they do not exist
    os.makedirs(i, exist_ok=True)
    os.makedirs(d, exist_ok=True)
    os.makedirs(b, exist_ok=True)
    os.makedirs(p, exist_ok=True)
    os.makedirs(os.path.join(p, "assets"), exist_ok=True)
    os.makedirs(os.path.join(p, "BabyFox"), exist_ok=True)

    # Read VERSION from the CDN and extract the semantic version of the latest release
    version_url = f"https://{domain}/swpwr/VERSION"
    version = requests.get(version_url).text.strip()

    # validate that the version is a semantic version. example: v1.2.300
    if not re.match(r"^v[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}$", version):
        raise ValueError(f"copy_assets() invalid version: {version} from {version_url}")

    # Download the latest swpwr release tarball
    tarball_url = f"https://{domain}/swpwr/swpwr-{version}.tar.gz"
    tarball_path = f"swpwr-{version}.tar.gz"
    with requests.get(tarball_url, stream=True) as r:
        with open(tarball_path, "wb", encoding="utf-8") as f:
            shutil.copyfileobj(r.raw, f)

    # Extract the tarball and move the contents to ~/src/
    with tarfile.open(tarball_path, "r:gz") as tar:
        tar.extractall(path=i)

    # Copy the swpwr .js .css and .woff2 files to public in swpwrxblock
    for ext in [".js", ".css", ".woff2"]:
        for file in os.listdir(b):
            if file.endswith(ext):
                shutil.copy(os.path.join(b, file), os.path.join(p, "assets" if ext == ".woff2" else ""))

    # Copy specific files
    for file in [
        "android-chrome-192x192.png",
        "android-chrome-512x512.png",
        "apple-touch-icon.png",
        "favicon-16x16.png",
        "favicon-32x32.png",
        "favicon.ico",
        "vite.svg",
        "site.webmanifest",
    ]:
        shutil.copy(os.path.join(d, file), p)

    shutil.copy(os.path.join(d, "BabyFox.svg"), p)
    shutil.copy(os.path.join(d, "BabyFox", "BabyFox.svg"), os.path.join(p, "BabyFox"))

    shutil.copy(os.path.join(i, "index.html"), p)
    with open(os.path.join(p, "index.html"), "r", encoding="utf-8") as file:
        data = file.read().replace(
            'gltfUrl: "/models/"',
            'gltfUrl: "https://s3.amazonaws.com/stepwise-editorial.querium.com/swpwr/dist/models/"',
        )
    with open(os.path.join(p, "index.html"), "w", encoding="utf-8") as file:
        file.write(data)

    # Get the most recent .js and .css files
    js1 = max([f for f in os.listdir(b) if f.endswith(".js")], key=lambda x: os.path.getmtime(os.path.join(b, x)))
    cs1 = max([f for f in os.listdir(b) if f.endswith(".css")], key=lambda x: os.path.getmtime(os.path.join(b, x)))

    shutil.copy(os.path.join(b, js1), p)
    shutil.copy(os.path.join(b, cs1), p)

    # Remember swpwr version info
    with open(os.path.join(p, "swpwr_version.json"), "w", encoding="utf-8") as f:
        f.write(f'{{"version": "{version}"}}')

    with open("swpwrxblock.py", "r", encoding="utf-8") as file:
        data = file.read().replace(
            "dashboard.bugfender.com/\\', version: \\'v?[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}",
            f"dashboard.bugfender.com/\\', version: \\'{version}",
        )
    with open("swpwrxblock.py", "w", encoding="utf-8") as file:
        file.write(data)

    logger(f"We are incorporating swpwr {version}")
    logger(f"The top-level Javascript file is {js1}")
    logger(f"The top-level CSS file is {cs1}")

    fix_css_url(css_filename=cs1)
    fix_js_url(js_filename=js1)

    # Update the HTML file with the new JS and CSS filenames
    swpwrxstudent_html_path = os.path.join(HERE, "swpwrxblock", "static", "html", "swpwrxstudent.html")
    logger(f"Updating {swpwrxstudent_html_path}")

    with open(swpwrxstudent_html_path, "r", encoding="utf-8") as file:
        data = file.read()
    data = data.replace(
        '<script type="module" crossorigin src="/static/xblock/resources/swpwrxblock/public.*$',
        f'<script type="module" crossorigin src="/static/xblock/resources/swpwrxblock/public/{js1}"></script>',
    )
    data = data.replace(
        '<link rel="module" crossorigin href="/static/xblock/resources/swpwrxblock/public.*$',
        f'<link rel="stylesheet" crossorigin href="/static/xblock/resources/swpwrxblock/public/{cs1}">',
    )
    with open(swpwrxstudent_html_path, "w", encoding="utf-8") as file:
        file.write(data)

    logger(f"Updated {swpwrxstudent_html_path}")
    logger("finished running swpwr installation script")


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
        "requests",
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
