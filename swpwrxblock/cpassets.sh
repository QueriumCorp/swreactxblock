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

# Which precache manifest to copy
# c=precache-manifest.8c5268b68a90c8397a5eb1681f40011c.js

ls $b | grep '\.js$' | sed -e "s#^#cp $b/#" -e 's#$# dist/#' | sh
ls $b | grep '\.woff2$' | sed -e "s#^#cp $b/#" -e 's#$# dist/#' | sh
ls $b | grep '\.css$' | sed -e "s#^#cp $b/#" -e 's#$# dist/#' | sh

# exit

# Which asset javascript files to copy
js1=index-xQGfimpM.js

# Which asset css files to copy
cs1=index-BlBmDmqs.css
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
if [ ! -d "dist" ]; then
  mkdir dist
fi
cp $b/${js1} dist/
#
cp $b/${cs1} dist/
