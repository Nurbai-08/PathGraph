import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";

import { AppProviders } from "./app/providers";
import { router } from "./app/router";
import "./styles.css";
import "@xyflow/react/dist/style.css";

const isLocalIp = import.meta.env.DEV && window.location.hostname === "127.0.0.1";

if (isLocalIp) {
  window.location.replace(
    `http://localhost:5173${window.location.pathname}${window.location.search}${window.location.hash}`,
  );
} else {
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>
    </StrictMode>,
  );
}
