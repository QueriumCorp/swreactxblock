#!/bin/bash
#
# version for loading the full swpwr app assets for SBIR Phase 2
#

# Full pathnames to the swpwr build and public directories
x=swpwr
i=~/src/$x
b=$i/dist/assets
p=$i/public
s=$i/src

if [ ! -d "dist" ]; then
  mkdir dist
fi
if [ ! -d "dist/assets" ]; then
  mkdir dist/assets
fi

if [ ! -d "public" ]; then
  mkdir public
fi
# Which precache manifest to copy
# c=precache-manifest.8c5268b68a90c8397a5eb1681f40011c.js

# Copy the swpwr .js .css and .woff2 files to public in swpwrxblock
ls $b | grep '\.js$' | sed -e "s#^#cp $b/#" -e 's#$# public/#' | sh
ls $b | grep '\.css$' | sed -e "s#^#cp $b/#" -e 's#$# public/#' | sh
ls $b | grep '\.woff2$' | sed -e "s#^#cp $b/#" -e 's#$# public/assets/#' | sh

# exit

# Which asset javascript files to copy.  Use the most recent one.
js1=`ls -t $b/*.js | head -1`
# js1=index-xQGfimpM.js

# Which asset css files to copy.  Use the most recent one.
cs1=`ls -t $b/*.css | head -1`
# cs1=index-BlBmDmqs.css
cp $p/android-chrome-192x192.png public/
cp $p/android-chrome-512x512.png public/
cp $p/apple-touch-icon.png public/
cp $p/favicon-16x16.png public/
cp $p/favicon-32x32.png public/
cp $p/favicon.ico public/
cp $p/vite.svg public/
#
cp $i/index.html public/
sed -I -e 's#/src/main.tsx#/public/main.tsx#' public/index.html
sed -I -e 's#gltfUrl: "/models/"#gltfUrl: "https://s3.amazonaws.com/stepwise-editorial.querium.com/swpwr/dist/models/"#' public/index.html
# cp $s/App.tsx public/
# cp $s/App.css public/
# cp $s/Stage.tsx public/
# cp $s/main.tsx public/
cp $s/assets/react.svg public/
# cp $s/models/foxy/model.tsx public/
#
cp $b/${js1} public/
#
cp $b/${cs1} public/

echo "Top-level Javascript file is $js1"
echo "Be sure to update that filename in swpwrxblock.py:"
echo "frag.add_javascript_url(\"public/${js1}\") # Need to update any time swpwr gets rebuilt"
