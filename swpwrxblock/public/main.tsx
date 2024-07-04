import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.tsx";

let gltfUrl = (window as any).swpwr.options.gltfUrl;
let swapiUrl = (window as any).swpwr.options.swapiUrl;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App gltfUrl={gltfUrl} swapiUrl={swapiUrl} />
  </React.StrictMode>
);
