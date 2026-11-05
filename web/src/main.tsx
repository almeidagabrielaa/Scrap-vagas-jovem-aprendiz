import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./estilos.css";

// App instalável (PWA): só no build de produção, para o modo dev não ficar preso a arquivos guardados.
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* sem service worker o site funciona igual, só não abre offline */
    });
  });
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
