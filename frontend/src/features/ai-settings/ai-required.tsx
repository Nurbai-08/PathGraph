import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import type { PropsWithChildren } from "react";
import { aiSettingsApi } from "../../entities/ai-settings/api";
import { t, useLocale } from "../../shared/lib/i18n";

export function AIRequired({ children }: PropsWithChildren) {
  useLocale();
  const settings = useQuery({ queryKey: ["ai-settings"], queryFn: aiSettingsApi.get, retry: false });
  if (settings.isLoading) return <p className="mt-3 text-sm">{t("Loading AI settings…")}</p>;
  if (!settings.data) return (
    <div className="mt-4 rounded-xl bg-amber-50 p-4 text-sm text-amber-950">
      <p>{t("Connect AI to get explanations, translations and quizzes. You can read sources and mark your progress now.")}</p>
      <Link to="/settings" className="mt-2 inline-block font-semibold underline">{t("Connect AI")}</Link>
    </div>
  );
  return children;
}
