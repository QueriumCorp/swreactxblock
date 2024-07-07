#/bin/sh
#
#Usage: tardist.sh 
#       Tars up the dist and public directories so they can be synched to Amazon S3
#       Uses scp to copy these to stepwise-editorial.querium.com
d=`date +"%Y%m%d%H%M"`
tar cvfz dist-$d.tar.gz dist
tar cvfz public-$d.tar.gz public
scp dist-$d.tar.gz root@stepwise-editorial.querium.com:/var/www/swpwr/
scp public-$d.tar.gz root@stepwise-editorial.querium.com:/var/www/swpwr/
