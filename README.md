# swpwrxblock

The StepWise Power (swpwr) xBlock for the edX LMS platform

## Developer Notes

This is cloned from the swxblock for StepWise

This block loads assets copied from the 'swpwr' repo

[https://github.com/QueriumCorp/swpwr](https://github.com/QueriumCorp/swpwr)

You'll need to update code in this repo if you re-run 'npm build' in the swpwr repo and you want
to use those new assets inside this xblock. For example, there are hard-coded 'chunk' assets, e.g. 'main.0048466c.chunk.js'
Specifically, you should look at the code in swpwrxblock/swpwrxblock.py that uses the fragment library to build
the student's HTML content view.

You can use the swpwrxblock/cpassets.sh script to fetch specific build asset files from a swpwr repo installation.

You may also need to run swpwrxblock/modifyreactassets.sh to modify the app.js and app.css assets so they begin full-screen and maximized.
We did this in Phase 1 in 2022.

## Build Notes

This package relies on customized build/install procedures that themselves are based on traditional Python tools including setup.py, setuptools, and setuptools. You'll find the entry point for our customization in setup():

```python
    cmdclass={
        "install": CustomInstall,
    },
```

Where `CustomInstall` is a Python class residing in customer_install.py in the root of this repo. CustomInstall is solely responsible for integrating the React app build artifacts of swpwr into the open edx XBlock defined in this package. CustomInstall implements a collection of hooks that we're using to download, transform, reorganize and add the swpwr React build artifacts to the Python package build created by Python's wheel application. The build process is platform independent and **should** result is working Xblock regardless of operating system; provided of course that Open edX itself deploys successfully.

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
