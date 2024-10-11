./tarscppublic.sh
git status | grep 'deleted:' | grep public | sed -e 's/both //' -e 's/deleted:/git rm /' | bash
git status | grep 'modified:' | grep public | sed -e 's/both //' -e 's/modified:/git add /' | bash
git add static/html/swpwrxstudent.html
git add public
cat public/swpwr_version.json
v=`cat public/swpwr_version.json | sed -e 's/^.*: \"//' -e 's/\"} *$//'`
echo Version is $v
git commit -m "Update swpwr version to $v"
git push
git status
echo "NOW: Consider merging palm.master into redwood.master, via:"
echo "  git checkout open-release/redwood.master"
echo "  git merge open-release/palm.master"
echo "  git push"
