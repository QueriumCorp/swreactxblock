#!/bin/bash
#
# Version of cpassets.sh that copies test assets from testReactxBlock
#
# Full pathnames to the swpwr build and public directories
x=testReactxBlock
i=~/src/$x/
b=$i/dist/assets
p=$i/public
s=$i/src

# Which precache manifest to copy
# c=precache-manifest.8c5268b68a90c8397a5eb1681f40011c.js

# Which asset javascript files to copy
js1=index-CIesktn4.js
# js1=1.72c79b30.chunk.js
# js2=main.e04ca138.chunk.js.map
# js3=runtime~main.229c360f.js.map
# js4=1.72c79b30.chunk.js.map
# js5=main.e04ca138.chunk.js
# js6=runtime~main.229c360f.js
#
# Which asset css files to copy
cs1=index-Ew53dMhJ.css
# cs1=1.7f8b3af7.chunk.css
# cs2=1.7f8b3af7.chunk.css.map
# cs3=main.b870043f.chunk.css
# cs4=main.b870043f.chunk.css.map
#
# cp $b/asset-manifest.json public/
# cp $p/favicon.ico public/
# cp $p/logo192.png public/
# cp $p/logo512.png public/
# cp $p/manifest.json public/
# cp $p/robots.txt public/
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
cp $s/App.tsx public/
cp $s/App.css public/
cp $s/Stage.tsx public/
cp $s/main.tsx public/
cp $s/assets/react.svg public/
cp $s/models/foxy/model.tsx public/
#
# cp $b/$c public/
# cp $b/service-worker.js public/
#
if [ ! -d "dist" ]; then
  mkdir dist
fi
cp $b/${js1} dist/
# cp $b/static/js/${js1} static/js/
# cp $b/static/js/${js2} static/js/
# cp $b/static/js/${js3} static/js/
# cp $b/static/js/${js4} static/js/
# cp $b/static/js/${js5} static/js/
# cp $b/static/js/${js6} static/js/
#
cp $b/${cs1} dist/
# cp $b/static/css/${cs1} static/css/
# cp $b/static/css/${cs1} static/css/
# cp $b/static/css/${cs3} static/css/
# cp $b/static/css/${cs4} static/css/
