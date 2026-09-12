import { t, useLocale } from "../shared/lib/i18n";
import { LogOut, Settings } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { PropsWithChildren } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuthStore } from "../entities/user/store";
import { authApi } from "../features/auth/api";
import { useCurrentUser } from "../features/auth/use-current-user";
import { Button } from "../shared/ui/button";

export function AppShell({ children }: PropsWithChildren) {
  useLocale();
  const { data: user } = useCurrentUser();
  const clearUser = useAuthStore((state) => state.clearUser);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const logout = useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      clearUser();
      queryClient.clear();
      navigate("/login", { replace: true });
    },
  });

  return (
    <div className="min-h-screen bg-cream text-ink">
      <header className="border-b border-ink/10 bg-cream/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8">
          <Link to="/" className="flex items-center gap-3 font-semibold tracking-tight">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-ink text-sm text-lime">PG</span>
            PathGraph
          </Link>
          <div className="flex items-center gap-1">
            <span className="mr-2 hidden text-sm text-ink/55 sm:block">{user?.email}</span>
            <Button variant="ghost" className="h-10 w-10 p-0" onClick={() => navigate("/settings")}>
              <Settings size={18} />
              <span className="sr-only">{t("Settings")}</span>
            </Button>
            <Button
              variant="ghost"
              className="h-10 w-10 p-0"
              onClick={() => logout.mutate()}
              disabled={logout.isPending}
            >
              <LogOut size={18} />
              <span className="sr-only">{t("Log out")}</span>
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8 sm:py-14">{children}</main>
    </div>
  );
}
