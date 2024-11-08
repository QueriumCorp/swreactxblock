# xblock assets in S3

This xblock uses the React assets for the 'swpwr' app from the QueriumCorp/swpwr repo in github.

At xblock install time, The setup.py downloads the latest assets from an S3 bucket and untars these into the react_build directory in the swpwrxblock.

For example:

https://swm-openedx-us-prod-storage.s3.us-east-2.amazonaws.com/swpwr/swpwr-v1.9.203.tar.gz

The VERSION file contains a string like this:

```
v1.9.203
```
