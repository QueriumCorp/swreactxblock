#!/bin/bash
if [ $# -ne 2 ];
    then echo "wrong number of parameters. must specify the javascript filename and the CSS filename to use."
fi
#    <script type=module crossorigin src=/static/xblock/resources/swreactxblock/public/index-CIjUOCFG.js></script>
#    <link rel=stylesheet crossorigin href=/static/xblock/resources/swreactxblock/public/index-KWNQs58g.css>
sed -i .bak -e 's#index-.*\\.js#$1#g' static/html/swreactxstudent.html
sed -i .bak2 -e 's#index-.*\\.css#$2#g' static/html/swreactxstudent.html
