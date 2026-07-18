import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { PreferencesForm } from "@/components/notifications/preferences-form";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import { getPreferences } from "@/lib/notification-prefs.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.notifications.preferences.title} · PrintForHelp` };
}

export default async function NotificationSettingsPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login?next=/settings/notifications");
  }
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value ?? "";
  const { dict } = await getServerI18n();
  const t = dict.notifications.preferences;
  const prefs = await getPreferences(token);

  return (
    <main className="mx-auto w-full max-w-2xl px-4 py-8">
      <h1 className="text-2xl font-semibold">{t.title}</h1>
      <p className="mt-1 text-sm text-muted">{t.subtitle}</p>
      <div className="mt-6">
        <PreferencesForm initial={prefs} />
      </div>
    </main>
  );
}
