import { create } from "zustand";
import { russian } from "./translations";

export type Locale = "ru" | "en";

function initialLocale(): Locale {
  try {
    return localStorage.getItem("pathgraph-language") === "en" ? "en" : "ru";
  } catch {
    return "ru";
  }
}

export const useLocale = create<{ locale: Locale; setLocale: (locale: Locale) => void }>((set) => ({
  locale: initialLocale(),
  setLocale: (locale) => {
    try { localStorage.setItem("pathgraph-language", locale); } catch { /* Storage is optional. */ }
    document.documentElement.lang = locale;
    set({ locale });
  },
}));

export function t(message: string): string {
  if (useLocale.getState().locale === "en") return message;
  return russian[message] ?? message;
}
