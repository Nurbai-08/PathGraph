import { t } from "../shared/lib/i18n";
import { Navigate, createBrowserRouter } from "react-router-dom";
import { lazy, Suspense, type ReactNode } from "react";

import { ProtectedLayout } from "./protected-layout";

const AuthPage = lazy(() =>
  import("../pages/auth/auth-page").then((module) => ({ default: module.AuthPage })),
);
const DashboardPage = lazy(() =>
  import("../pages/dashboard/dashboard-page").then((module) => ({ default: module.DashboardPage })),
);
const SettingsPage = lazy(() =>
  import("../pages/settings/settings-page").then((module) => ({ default: module.SettingsPage })),
);
const WorkspacePage = lazy(() =>
  import("../pages/workspace/workspace-page").then((module) => ({ default: module.WorkspacePage })),
);

export const router = createBrowserRouter([
  { path: "/login", element: loadPage(<AuthPage mode="login" />) },
  { path: "/register", element: loadPage(<AuthPage mode="register" />) },
  {
    element: <ProtectedLayout />,
    children: [
      { path: "/", element: loadPage(<DashboardPage />) },
      { path: "/workspace/:id", element: loadPage(<WorkspacePage />) },
      { path: "/settings", element: loadPage(<SettingsPage />) },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);

function loadPage(page: ReactNode) {
  return <Suspense fallback={<p className="text-sm text-ink/50">{t("Loading…")}</p>}>{page}</Suspense>;
}
