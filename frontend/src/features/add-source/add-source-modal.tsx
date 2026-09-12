import { t, useLocale } from "../../shared/lib/i18n";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileText, Link2, Plus, Type, Upload, X } from "lucide-react";
import { useRef, useState, type FormEvent } from "react";

import { sourceApi } from "../../entities/source/api";
import { ApiError } from "../../shared/api/client";
import type { SourceInput, SourceType } from "../../shared/types/source";
import { Button } from "../../shared/ui/button";
import { Card } from "../../shared/ui/card";
import { Input } from "../../shared/ui/input";
import { ErrorMessage } from "../../shared/ui/status";
import { Textarea } from "../../shared/ui/textarea";

const sourceTypes = [
  { value: "url" as const, label: "URL", icon: Link2 },
  { value: "text" as const, label: "Text", icon: Type },
  { value: "pdf" as const, label: "PDF", icon: FileText },
];

export function AddSourceModal({ workspaceId, onAdded }: { workspaceId: string; onAdded?: (sourceId: string) => void }) {
  useLocale();
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<SourceType>("url");
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | undefined>();
  const inputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: sourceApi.create,
    onSuccess: async (source) => {
      await queryClient.invalidateQueries({ queryKey: ["sources", workspaceId] });
      onAdded?.(source.id);
      reset();
    },
  });

  function reset() {
    mutation.reset();
    setOpen(false);
    setTitle("");
    setUrl("");
    setText("");
    setFile(undefined);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const input: SourceInput = { workspaceId, type, title: title || defaultTitle(type, file) };
    if (type === "url") input.url = url;
    if (type === "text") input.text = text;
    if (type === "pdf") input.file = file;
    mutation.mutate(input);
  }

  if (!open) {
    return <Button onClick={() => setOpen(true)}><Plus size={17} /> {t("Add Source")}</Button>;
  }

  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center bg-ink/35 p-4 backdrop-blur-sm">
      <Card className="w-full max-w-xl p-6 sm:p-8">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-moss">{t("New material")}</p>
            <h2 className="mt-2 text-2xl font-semibold">{t("Add a source")}</h2>
          </div>
          <Button variant="ghost" className="h-9 w-9 p-0" onClick={reset}>
            <X size={18} /><span className="sr-only">{t("Close")}</span>
          </Button>
        </div>

        <div className="mt-6 grid grid-cols-3 gap-2 rounded-2xl bg-cream p-1.5">
          {sourceTypes.map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => setType(item.value)}
              className={`flex items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${
                type === item.value ? "bg-white text-ink shadow-sm" : "text-ink/45 hover:text-ink"
              }`}
            >
              <item.icon size={16} /> {t(item.label)}
            </button>
          ))}
        </div>

        <form className="mt-6 space-y-4" onSubmit={submit}>
          <label className="block space-y-2 text-sm font-medium"> {t("Title")} <span className="font-normal text-ink/40">{t("(optional)")}</span>
            <Input value={title} maxLength={300} onChange={(event) => setTitle(event.target.value)} />
          </label>
          {type === "url" && (
            <label className="block space-y-2 text-sm font-medium"> {t("Public URL")} <Input
                required
                type="url"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://example.com/guide"
              />
            </label>
          )}
          {type === "text" && (
            <label className="block space-y-2 text-sm font-medium"> {t("Text")} <Textarea
                required
                className="min-h-40"
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder={t("Paste notes, an article, or documentation…")}
              />
            </label>
          )}
          {type === "pdf" && (
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="flex w-full flex-col items-center rounded-2xl border border-dashed border-ink/20 bg-cream/50 px-5 py-8 text-center transition hover:border-moss"
            >
              <Upload className="text-moss" size={24} />
              <span className="mt-3 text-sm font-semibold">{file?.name ?? t("Choose a PDF")}</span>
              <span className="mt-1 text-xs text-ink/40">{t("Maximum 10 MB")}</span>
              <input
                ref={inputRef}
                hidden
                required
                type="file"
                accept="application/pdf,.pdf"
                onChange={(event) => setFile(event.target.files?.[0])}
              />
            </button>
          )}
          {mutation.error && (
            <ErrorMessage
              message={mutation.error instanceof ApiError ? mutation.error.message : t("Could not add source.")}
            />
          )}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={reset}>{t("Cancel")}</Button>
            <Button type="submit" disabled={mutation.isPending || (type === "pdf" && !file)}>
              {mutation.isPending ? t("Adding…") : t("Analyze source")}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

function defaultTitle(type: SourceType, file: File | undefined): string {
  if (type === "pdf") return file?.name ?? t("PDF source");
  if (type === "text") return t("Text source");
  return "";
}
