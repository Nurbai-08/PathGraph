import { useEffect } from "react";
import { useLocale } from "../lib/i18n";

export function LanguageSwitcher() {
  const { locale, setLocale } = useLocale();
  useEffect(() => { document.documentElement.lang = locale; }, [locale]);
  return (
    <div className="fixed bottom-4 left-4 z-50 flex gap-1 rounded-full border border-ink/15 bg-white p-1 shadow-sm" role="group" aria-label="Язык / Language">
      {(["ru", "en"] as const).map((value) => (
        <button key={value} type="button" aria-pressed={locale === value}
          className={`rounded-full px-3 py-2 text-sm font-semibold ${locale === value ? "bg-ink text-white" : "text-ink/60"}`}
          onClick={() => setLocale(value)}>{value.toUpperCase()}</button>
      ))}
    </div>
  );
}
