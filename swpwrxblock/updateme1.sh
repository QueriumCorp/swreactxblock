git checkout open-release/redwood.master
git branch
cd swpwrxblock
d=`date '+%Y%m%d%H%M'`
tar cvfz public-$d-backup.tar.gz public
rm -rf public
./cpassets.sh
