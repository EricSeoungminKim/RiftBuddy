import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";

document.documentElement.style.background = "transparent";
document.documentElement.style.overflow = "hidden";
document.body.style.margin = "0";
document.body.style.background = "transparent";
document.body.style.overflow = "hidden";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
