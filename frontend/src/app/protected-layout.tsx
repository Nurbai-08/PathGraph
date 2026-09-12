import { Navigate, Outlet } from "react-router-dom";

import { useCurrentUser } from "../features/auth/use-current-user";
import { PageLoader } from "../shared/ui/status";
import { AppShell } from "../widgets/app-shell";

export function ProtectedLayout() {
  const currentUser = useCurrentUser();

  if (currentUser.isLoading) return <PageLoader />;
  if (!currentUser.data) return <Navigate to="/login" replace />;

  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}

