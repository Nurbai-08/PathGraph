import { t, useLocale } from "../../shared/lib/i18n";
import { ArrowLeft, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { useCurrentUser } from "../../features/auth/use-current-user";
import { AISettingsPanel } from "../../features/ai-settings/ai-settings-panel";
import { Card } from "../../shared/ui/card";

export function SettingsPage() {
  useLocale();
  const { data: user } = useCurrentUser();

  return (
    <div className="max-w-2xl">
      <Link to="/" className="inline-flex items-center gap-2 text-sm font-medium text-ink/50 hover:text-moss">
        <ArrowLeft size={16} /> {t("Dashboard")} </Link>
      <h1 className="mt-8 text-4xl font-semibold tracking-tight">{t("Settings")}</h1>
      <Card className="mt-8 p-6 sm:p-8">
        <div className="flex items-center gap-4">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-moss/10 text-moss">
            <ShieldCheck size={22} />
          </span>
          <div>
            <p className="text-sm font-semibold">{t("Account")}</p>
            <p className="mt-1 text-sm text-ink/50">{t("Your authenticated PathGraph profile")}</p>
          </div>
        </div>
        <dl className="mt-8 border-t border-ink/10 pt-6">
          <div className="flex items-center justify-between gap-4">
            <dt className="text-sm text-ink/50">{t("Email")}</dt>
            <dd className="text-sm font-medium">{user?.email}</dd>
          </div>
        </dl>
      </Card>
      <AISettingsPanel />
    </div>
  );
}
