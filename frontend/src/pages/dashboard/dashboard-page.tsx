import { t, useLocale } from "../../shared/lib/i18n";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Boxes, Code2 } from "lucide-react";
import { Link } from "react-router-dom";

import { workspaceApi } from "../../entities/workspace/api";
import { CreateWorkspaceForm } from "../../features/create-workspace/create-workspace-form";
import { Card } from "../../shared/ui/card";
import { ErrorMessage } from "../../shared/ui/status";

export function DashboardPage() {
  useLocale();
  const workspaces = useQuery({ queryKey: ["workspaces"], queryFn: workspaceApi.list });

  return (
    <div>
      <div className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-moss">{t("Your library")}</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">{t("Your Workspaces")}</h1>
          <p className="mt-3 text-ink/55">{t("One clear home for every subject you want to master.")}</p>
        </div>
        <CreateWorkspaceForm />
      </div>

      {workspaces.isError && (
        <div className="mt-8"><ErrorMessage message={t("Could not load your workspaces.")} /></div>
      )}

      {workspaces.isLoading && <p className="mt-12 text-sm text-ink/50">{t("Loading workspaces…")}</p>}

      {workspaces.data?.length === 0 && (
        <Card className="mt-10 border-dashed bg-white/60 p-10 text-center sm:p-16">
          <Boxes className="mx-auto text-moss" size={34} />
          <h2 className="mt-5 text-xl font-semibold">{t("A clean slate for your next subject")}</h2>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink/50"> {t("Create a workspace now. Sources and knowledge connections arrive in the next phase.")} </p>
        </Card>
      )}

      <div className="mt-10 grid gap-5 md:grid-cols-2">
        {workspaces.data?.map((workspace, index) => (
          <Link key={workspace.id} to={`/workspace/${workspace.id}`}>
            <Card className="group h-full overflow-hidden p-6 transition hover:-translate-y-1 hover:border-moss/30">
              <div className="flex items-start justify-between">
                <span className="grid h-11 w-11 place-items-center rounded-2xl bg-moss/10 text-moss">
                  {index % 2 === 0 ? <Code2 size={20} /> : <Boxes size={20} />}
                </span>
                <ArrowUpRight className="text-ink/30 transition group-hover:text-moss" size={20} />
              </div>
              <h2 className="mt-8 text-xl font-semibold">{workspace.name}</h2>
              <p className="mt-2 line-clamp-2 min-h-10 text-sm leading-5 text-ink/50">
                {workspace.description || t("Ready for your first learning source.")}
              </p>
              <p className="mt-6 text-xs font-semibold uppercase tracking-[0.16em] text-moss"> {t("Open workspace")} </p>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
