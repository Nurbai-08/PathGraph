import { t, useLocale } from "../../shared/lib/i18n";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { useState, type FormEvent } from "react";

import { workspaceApi } from "../../entities/workspace/api";
import { ApiError } from "../../shared/api/client";
import { Button } from "../../shared/ui/button";
import { Card } from "../../shared/ui/card";
import { ErrorMessage } from "../../shared/ui/status";
import { Input } from "../../shared/ui/input";
import { Textarea } from "../../shared/ui/textarea";

export function CreateWorkspaceForm() {
  useLocale();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: workspaceApi.create,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      setName("");
      setDescription("");
      setOpen(false);
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate({ name, description });
  }

  if (!open) {
    return (
      <Button onClick={() => setOpen(true)}>
        <Plus size={17} /> {t("New Workspace")} </Button>
    );
  }

  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center bg-ink/35 p-4 backdrop-blur-sm">
      <Card className="w-full max-w-lg p-6 sm:p-8">
        <div className="mb-6 flex items-start justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-moss">{t("New space")}</p>
            <h2 className="mt-2 text-2xl font-semibold">{t("What will you learn?")}</h2>
          </div>
          <Button variant="ghost" className="h-9 w-9 p-0" onClick={() => setOpen(false)}>
            <X size={18} />
            <span className="sr-only">{t("Close")}</span>
          </Button>
        </div>
        <form className="space-y-4" onSubmit={submit}>
          <label className="block space-y-2 text-sm font-medium"> {t("Name")} <Input
              required
              maxLength={120}
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder={t("Python Backend")}
              autoFocus
            />
          </label>
          <label className="block space-y-2 text-sm font-medium"> {t("Description")} <Textarea
              maxLength={2000}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder={t("What do you want this workspace to help you understand?")}
            />
          </label>
          {mutation.error && (
            <ErrorMessage
              message={
                mutation.error instanceof ApiError ? mutation.error.message : t("Could not create workspace.")
              }
            />
          )}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={() => setOpen(false)}> {t("Cancel")} </Button>
            <Button type="submit" disabled={mutation.isPending || name.trim().length === 0}>
              {mutation.isPending ? t("Creating…") : t("Create workspace")}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
