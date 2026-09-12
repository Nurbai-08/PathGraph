import { t, useLocale } from "../lib/i18n";
export function PageLoader() {
  useLocale();
  return (
    <div className="flex min-h-screen items-center justify-center bg-cream text-sm text-ink/55"> {t("Loading PathGraph…")} </div>
  );
}

export function ErrorMessage({ message }: { message: string }) {
  useLocale();
  return (
    <p role="alert" className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">
      {t(message)}
    </p>
  );
}
