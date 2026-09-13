import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2, X } from "lucide-react";
import { useState } from "react";
import { createPortal } from "react-dom";

import { workspaceApi } from "../../entities/workspace/api";
import { ApiError } from "../../shared/api/client";
import { t, useLocale } from "../../shared/lib/i18n";
import { Button } from "../../shared/ui/button";
import { Card } from "../../shared/ui/card";
import { ErrorMessage } from "../../shared/ui/status";

type DeleteWorkspaceButtonProps = {
  workspaceId: string;
  workspaceName: string;
  compact?: boolean;
  onDeleted?: () => void;
};

export function DeleteWorkspaceButton({
  workspaceId,
  workspaceName,
  compact = false,
  onDeleted,
}: DeleteWorkspaceButtonProps) {
  useLocale();
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => workspaceApi.delete(workspaceId),
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: ["workspace", workspaceId] });
      queryClient.removeQueries({ queryKey: ["sources", workspaceId] });
      queryClient.removeQueries({ queryKey: ["graph", workspaceId] });
      queryClient.removeQueries({ queryKey: ["learning-paths", workspaceId] });
      await queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      setOpen(false);
      onDeleted?.();
    },
  });

  function close() {
    if (mutation.isPending) return;
    mutation.reset();
    setOpen(false);
  }

  return (
    <>
      <Button
        variant={compact ? "ghost" : "secondary"}
        className={compact ? "relative z-10 h-9 w-9 shrink-0 p-0 text-ink/40 hover:text-red-700" : "text-red-700 hover:border-red-300"}
        onClick={() => setOpen(true)}
        aria-label={t("Delete workspace")}
      >
        <Trash2 size={compact ? 16 : 17} />
        {!compact && t("Delete workspace")}
      </Button>

      {open && createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/35 p-4 backdrop-blur-sm">
          <Card
            className="w-full max-w-lg p-6 sm:p-8"
            role="dialog"
            aria-modal="true"
            aria-labelledby={`delete-workspace-${workspaceId}`}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-red-700">{t("Danger zone")}</p>
                <h2 id={`delete-workspace-${workspaceId}`} className="mt-2 text-2xl font-semibold">
                  {t("Delete workspace?")}
                </h2>
              </div>
              <Button variant="ghost" className="h-9 w-9 p-0" onClick={close} disabled={mutation.isPending}>
                <X size={18} /><span className="sr-only">{t("Close")}</span>
              </Button>
            </div>

            <p className="mt-5 text-sm leading-6 text-ink/60">
              {t("This will permanently delete the workspace and all its materials, graphs, and learning progress.")}
            </p>
            <p className="mt-3 rounded-2xl bg-red-50 px-4 py-3 font-semibold text-red-800">{workspaceName}</p>

            {mutation.error && (
              <div className="mt-4">
                <ErrorMessage message={t(mutation.error instanceof ApiError ? mutation.error.message : "Could not delete workspace.")} />
              </div>
            )}

            <div className="mt-6 flex justify-end gap-3">
              <Button variant="ghost" onClick={close} disabled={mutation.isPending}>{t("Cancel")}</Button>
              <Button variant="danger" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
                <Trash2 size={17} /> {mutation.isPending ? t("Deleting…") : t("Delete permanently")}
              </Button>
            </div>
          </Card>
        </div>,
        document.body,
      )}
    </>
  );
}
