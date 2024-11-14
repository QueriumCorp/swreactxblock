# swpwrxblock

The StepWise Power (swpwr) xBlock for the edX LMS platform. Implements the [swpwr](https://github.com/QueriumCorp/swpwr) React app. This package is environment specific, and defaults to `prod`. During builds (which are managed by tutor) we rely on a custom tutor environment variable, `STEPWISEMATH_ENV`, implemented via the tutor plugin [StepwiseMath/tutor-contrib-stepwise-config](https://github.com/StepwiseMath/tutor-contrib-stepwise-config).

_Note: you may also need to run swpwrxblock/modifyreactassets.sh to modify the app.js and app.css assets so they begin full-screen and maximized. We did this in Phase 1 in 2022._

## Build Notes

This package relies on pip-based customized build/install procedures that themselves are based on traditional Python tools including setup.py, setuptools, and setuptools. You'll find the entry point for our customization in setup():

```python
    cmdclass={
        "install": CustomInstall,
    },
```

Where `CustomInstall` is a Python class residing in customer_install.py in the root of this repo. CustomInstall is solely responsible for integrating the React app build artifacts of swpwr into the open edx XBlock defined in this package. CustomInstall implements a collection of hooks that we're using to download, transform, reorganize and add the swpwr React build artifacts to the Python package build created by Python's wheel application. The build process is platform independent and **should** result is working Xblock regardless of operating system; provided of course that Open edX itself deploys successfully.

### PEP-517 and PEP-518

Noting that setup.py is now deprecated, we've done as much as presently can be done to make our customized build-install compliant with new PEP-517 and PEP-518 guidelines. As of this publication (Nov-2024) there are no programmatic hooks available that would allow us to inject additional build steps into pip's wheel build procedure.

### ReactJS app integration notes

This xblock integrates [https://github.com/QueriumCorp/swpwr](https://github.com/QueriumCorp/swpwr) which involves several considerations:

- React's `<div id="root"></div>` hooks needs to dovetail into Django's traditional UI templating concepts
- swpwr itself needs an awareness that it will run alongside other noon-related React code in the browser, due to open edx's new MFE-based UI
- the swpwr React build has to be partially disassembled and re-assembled into open edx's static asset delivery mechanisms
- the build process needs remain managed by `pip install ...` such that fully automated build-deploy CI-CD processes work successfully.

swpwr itself it built and distributed via AWS S3/Cloudfront in either of three environment-specific builds for dev, staging, prod. The React build artifacts are retrieved from Cloudfront during pip install.

uses the React assets for the 'swpwr' app from the QueriumCorp/swpwr repo in github.

At xblock install time, The setup.py downloads the latest assets from an S3 bucket and untars these into the react_build directory in the swpwrxblock.

For example:

https://swm-openedx-us-prod-storage.s3.us-east-2.amazonaws.com/swpwr/swpwr-v1.9.203.tar.gz

The VERSION file contains a string like this: `v1.9.203`
