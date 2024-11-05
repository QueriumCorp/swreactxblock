#!/bin/bash
#
# version for loading the full swpwr app assets for SBIR Phase 2
#


if [ $# -eq 1 ]; then
  environment=$1
else
  environment="prod"
fi

# Set the environment based CDN URL
case $environment in
  dev)
    domain="cdn.dev.stepwisemath.ai"
    ;;
  prod)
    domain="cdn.web.stepwisemath.ai"
    ;;
  staging)
    domain="cdn.staging.stepwisemath.ai"
    ;;
  *)
    echo "Invalid environment: $environment"
    exit 1
    ;;
esac

# Full pathnames to the swpwr build and public directories
i=../react_build/
d=$i/dist
b=$d/assets

# mcdaniel: this MIGHT need to be ../swpwrxblock/public
p=../swpwrxblock/public

# read VERSION from the cdn and extract the semantic version of the latest release
version=$(curl https://${domain}/swpwr/VERSION)

# Download the latest swpwr release tarball
curl -O https://${domain}/swpwr/swpwr-${version}.tar.gz

# Extract the tarball and move the contents to ~/src/
tar -xvf swpwr-${version}.tar.gz -C $i

# ----------------------------
# sample folder structure
# ~/react_build/
#   dist/
#     assets/
#     BabyFox/
#     models/
#     index.html
# ----------------------------


if [ ! -d $d ]; then
  # raise an error if the dist directory does not exist
  echo "dist directory does not exist"
  exit 1
fi
if [ ! -d $b ]; then
  # raise an error if the dist/assets directory does not exist
  echo "dist/assets directory does not exist"
  exit 1
fi

if [ ! -d "$p/assets" ]; then
  mkdir -p $p/assets
  echo "$p/assets directory created"
fi


if [ ! -d "$p/BabyFox" ]; then
  mkdir -p $p/BabyFox
  echo "$p/BabyFox directory created"
fi

# Which precache manifest to copy
# c=precache-manifest.8c5268b68a90c8397a5eb1681f40011c.js

# Copy the swpwr .js .css and .woff2 files to public in swpwrxblock
ls $b | grep '\.js$' | sed -e "s#^#cp $b/#" -e "s#$# $p/#" | sh
ls $b | grep '\.css$' | sed -e "s#^#cp $b/#" -e "s#$# $p/#" | sh
ls $b | grep '\.woff2$' | sed -e "s#^#cp $b/#" -e "s#$# $p/assets/#" | sh

# exit

# Which asset javascript files to copy.  Use the most recent one.
js1=`ls -t $b/*.js | sed -e 's#^.*/##g' | head -1`
# echo js1=$js1
# js1=index-xQGfimpM.js

# Which asset css files to copy.  Use the most recent one.
cs1=`ls -t $b/*.css | sed -e 's#^.*/##g' | head -1`
# cs1=index-BlBmDmqs.css
# echo cs1=$cs1

cp $d/android-chrome-192x192.png $p/
cp $d/android-chrome-512x512.png $p/
cp $d/apple-touch-icon.png $p/
cp $d/favicon-16x16.png $p/
cp $d/favicon-32x32.png $p/
cp $d/favicon.ico $p/
cp $d/vite.svg $p/
#
cp $d/site.webmanifest $p/
#
# We are not using foxy.glb as of Sept 19, 2024 to remove 25MB of payload from the swpwrxblock assets and not to try to download the file from S3
# cp $m/foxy.glb public/models/
cp $d/BabyFox.svg $p/BabyFox.svg
cp $d/BabyFox/BabyFox.svg $p/BabyFox/BabyFox.svg
#
cp $i/index.html $p/
sed -I -e 's#gltfUrl: "/models/"#gltfUrl: "https://s3.amazonaws.com/stepwise-editorial.querium.com/swpwr/dist/models/"#' $p/index.html

#
cp $b/${js1} $p/
#
cp $b/${cs1} $p/

# Remember swpwr version info
# {  "version": "1.9.200"}
echo "$version" > $p/swpwr_version.json
# v1=`grep '^  "version":' $i/package.json | sed -e 's/^.*: "//' -e 's/"}//' -e 's/",//'`
sed -I -e "s#dashboard.bugfender.com/\\\', version: \\\'v?[0-9]\{1,3\}.[0-9]\{1,3\}.[0-9]\{1,3\}#dashboard.bugfender.com/\\\', version: \\\'${version}#" swpwrxblock.py

echo "We are incorporating swpwr $version"
echo "The top-level Javascript file is $js1"
echo "The top-level CSS file is $cs1"
echo "Going to run:"
echo "./fixcssurl.sh $cs1"
echo "./fixcssurl.sh $cs1" | /bin/bash
echo "Going to run:"
echo "./fixjsurl.sh $js1"
echo "./fixjsurl.sh $js1"  | /bin/bash

# echo "Be sure to edit static/html/swpwrxstudent.html to update those filenames:"
echo "Editing static/html/swpwrxstudent.html to specify:"
echo "${js1}"
echo "${cs1}"
# echo "    <!-- Load main React app filename -->"
# echo "    <script type="module" crossorigin src="/static/xblock/resources/swpwrxblock/public/${js1}"></script>"
sed -I -e "s/<script type=\"module\" crossorigin src=\"\/static\/xblock\/resources\/swpwrxblock\/public.*$/<script type=\"module\" crossorigin src=\"\/static\/xblock\/resources\/swpwrxblock\/public\/{$js1}\"><\/script>/" static/html/swpwrxstudent.html
# echo "    <link rel="stylesheet" crossorigin href="/static/xblock/resources/swpwrxblock/public/${cs1}">"
sed -I -e "s/<link rel="module" crossorigin href=\"\/static\/xblock\/resources\/swpwrxblock\/public.*$/<link rel=\"stylesheet\" crossorigin href=\"\/static\/xblock\/resources\/swpwrxblock\/public\/{$cs1}\">/" static/html/swpwrxstudent.html
echo "Done with cpassets.sh"
