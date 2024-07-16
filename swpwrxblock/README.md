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
The output of cpassets.sh will tell you what else you need to do:
(a) Edit static/html/swxpwrxstudent.html to change the filenames of the main javscript and css files.
(b) Run fixjsurl.sh.
(c) Run fixcssurl.sh

3. You can then run 'tardist.sh' to copy these assets to stepwise-editorial.querium.com.  You'll need to be able to connect to stepwise-editorial.querium.com as root using rsh for the following command to work:
```
./tarscppublic.sh
```

4. You need to use ssh to login to stepwise-editorial.querium.com and 'rotate' the dist and public directories so they'll be correct in the S3 bucket when they synch up at the top of each hour.
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
