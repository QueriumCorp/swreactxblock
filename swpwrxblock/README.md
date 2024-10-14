# Creating xblock assets in S3

To copy the necessary React assets from the swpwr app for use by this xblock, here are the steps:

1. In the swpwr repo build directory (e.g. /home/kent/src/swpwr):

```
npm install
npm run dev
npm run build
```

2. Then, in the swpwrxblock build directory (e.g. /home/kent/src/swpwrxblock/swpwrxblock) you'll need to run :
```
cpassets.sh
```
This will copy the assets from the swpwr build directory into the swpwrxblock build directory.

3.  The output of cpassets.sh will tell you what you need to do next:
(a) Edit static/html/swxpwrxstudent.html to change the filenames of the main javscript and css files.
(b) Run fixjsurl.sh.
(c) Run fixcssurl.sh

4. You can then run 'tardist.sh' to copy these assets to stepwise-editorial.querium.com.  You'll need to be able to connect to stepwise-editorial.querium.com as root using rsh for the following command to work:
```
./tarscppublic.sh
```

5. You need to use ssh to login to stepwise-editorial.querium.com and 'rotate' the dist and public directories so they'll be correct in the S3 bucket when they synch up at the top of each hour.
```
ssh root@stepwise-editorial.querium.com
```
# Then on stepwise-editorial as root:
```
cd /var/www/swpwr
rm -rf public # Unlink old version of public

tar xvfz public-YYYYMMDDHHMM.tar.gz
mv public public-YYYYMMDDHHMM
ln -s public-YYYYMMDDHHMM public

/root/aws-s3-sync.sh #Force re-sync to S3
```

6. Once you are comfortable with the above, you can automate steps 1, 4, and 5 via these shell scripts:
```
updateme1.sh
# Then do step 2 above by hand (edit swpwrxblock.html, run fixjsurl.sh, run fixcssurl.sh).
# Then run this:
updateme2.sh
# The above will commit the results to open-release/palm.master branch on github.
# If updateme2.sh seems to work to update the results in open-release/palm.master, you can then run:
updateme3.sh
# This final of the 3 scripts merges the changes made to open-release/palm.master into the open-release/redwood.master and main branches.
```
