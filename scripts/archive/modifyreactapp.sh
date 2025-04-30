#!/bin/bash
# Modify the React app assets app.js and app.css to support maximization by default, and to be full-screen when maximized
# For app.js:
# kentfuka@Kents-Mac-mini swreact % diff -c public/assets/app.js ~/src/swreactxblock/swreactxblock/public/assets/app.js
# *** public/assets/app.js	2022-11-14 09:28:07.000000000 -0700
# --- /Users/kentfuka/src/swreactxblock/swreactxblock/public/assets/app.js	2022-11-15 11:47:17.000000000 -0700
# ***************
# *** 31609,31615 ****
#       const onSubmit = props.onSubmit;
#       const initializedWork = props.problem ? { ...blankWork, problem: props.problem } : { ...blankWork };
#       const [work, workDispatch] = (0, import_react108.useReducer)(reducer_default, initializedWork);
# !     const [maximized, setMaximized] = (0, import_react108.useState)(false);
#       return /* @__PURE__ */ import_react108.default.createElement("div", {
#         className: "SWPowerComponent " + (maximized ? "Maximized" : "")
#       }, /* @__PURE__ */ import_react108.default.createElement(Wizard, {
# --- 31609,31615 ----
#       const onSubmit = props.onSubmit;
#       const initializedWork = props.problem ? { ...blankWork, problem: props.problem } : { ...blankWork };
#       const [work, workDispatch] = (0, import_react108.useReducer)(reducer_default, initializedWork);
# !     const [maximized, setMaximized] = (0, import_react108.useState)(true);
#       return /* @__PURE__ */ import_react108.default.createElement("div", {
#         className: "SWPowerComponent " + (maximized ? "Maximized" : "")
#       }, /* @__PURE__ */ import_react108.default.createElement(Wizard, {
# ***************
# *** 31617,31623 ****
#           problem: work.problem,
#           maximized,
#           setMaximized,
# !         maximizable: false
#         }),
#         footer: /* @__PURE__ */ import_react108.default.createElement(reactFooter_default, {
#           problem: work.problem,
# --- 31617,31623 ----
#           problem: work.problem,
#           maximized,
#           setMaximized,
# !         maximizable: true
#         }),
#         footer: /* @__PURE__ */ import_react108.default.createElement(reactFooter_default, {
#           problem: work.problem,
#
# For app.css:
# kentfuka@Kents-Mac-mini swreact % diff -c public/assets/app.css ~/src/swreactxblock/swreactxblock/public/assets/app.css
# *** public/assets/app.css	2022-11-14 09:28:07.000000000 -0700
# --- /Users/kentfuka/src/swreactxblock/swreactxblock/public/assets/app.css	2022-11-15 14:33:17.000000000 -0700
# ***************
# *** 9599,9607 ****
# --- 9599,9610 ----
#   .Maximized {
#     background: white;
#     position: fixed;
# +   left: 0px;
#     top: 0px;
#     min-height: 100vh;
#     max-height: 100vh;
# +   width: 100%;
# +   max-width: 100%;
#     border: solid 1px black;
#   }
sed -I .bak -e 's/const \[maximized, setMaximized\] = (0, import_react108\.useState)(false);/const [maximized, setMaximized] = (0, import_react108.useState)(true);/' -e 's/maximizable: false/maximizable: true/' swreactxblock/public/assets/app.js
sed -I .bak -e 's/Maximized {/Maximized {\n    left: 0px;\n    width: 100%;\n    max-width: 100%;/' swreactxblock/public/assets/app.css
echo diffing app.js
diff swreactxblock/public/assets/app.js swreactxblock/public/assets/app.js.bak
echo diffing app.css
diff swreactxblock/public/assets/app.css swreactxblock/public/assets/app.css.bak
