swpwrxblock
========

The StepWise Power (swpwr) xBlock for the edX LMS platform

Developer Notes
-------------
This is cloned from the swxblock for StepWise

This block loads assets copied from the 'swpwr' repo 

https://github.com/QueriumCorp/swpwr

You'll need to update code in this repo if you re-run 'npm build' in the swpwr repo and you want
to use those new assets inside this xblock. For example, there are hard-coded 'chunk' assets, e.g. 'main.0048466c.chunk.js'
Specifically, you should look at the code in swpwrxblock/swpwrxblock.py that uses the fragment library to build
the student's HTML content view.

You can use the swpwrxblock/cpassets.sh script to fetch specific build asset files from a swpwr repo installation.

You may also need to run swpwrxblock/modifyreactassets.sh to modify the app.js and app.css assets so they begin full-screen and maximized.
We did this in Phase 1 in 2022.
