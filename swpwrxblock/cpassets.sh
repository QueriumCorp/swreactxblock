#!/bin/bash
b=~/src/swpwr/build
p=~/src/swpwr/public
c=precache-manifest.8c5268b68a90c8397a5eb1681f40011c.js
js1=1.72c79b30.chunk.js
js2=main.e04ca138.chunk.js.map
js3=runtime~main.229c360f.js.map
js4=1.72c79b30.chunk.js.map
js5=main.e04ca138.chunk.js
js6=runtime~main.229c360f.js
#
cs1=1.7f8b3af7.chunk.css
cs2=1.7f8b3af7.chunk.css.map
cs3=main.b870043f.chunk.css
cs4=main.b870043f.chunk.css.map
#
cp $b/asset-manifest.json public/
cp $p/favicon.ico public/
cp $p/logo192.png public/
cp $p/logo512.png public/
cp $p/manifest.json public/
cp $p/robots.txt public/
#
cp $b/$c public/
cp $b/service-worker.js public/
#
cp $b/static/js/${js1} static/js/
cp $b/static/js/${js2} static/js/
cp $b/static/js/${js3} static/js/
cp $b/static/js/${js4} static/js/
cp $b/static/js/${js5} static/js/
cp $b/static/js/${js6} static/js/
#
cp $b/static/css/${cs1} static/css/
cp $b/static/css/${cs1} static/css/
cp $b/static/css/${cs3} static/css/
cp $b/static/css/${cs4} static/css/
