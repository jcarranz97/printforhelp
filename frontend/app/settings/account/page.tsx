import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { AccountForm } from "@/components/settings/account-form";
import { SettingsNav } from "@/components/settings/settings-nav";
import { getServerI18n } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.settingsProfile.accountPageTitle} · PrintForHelp` };
}

export default async function AccountSettingsPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login?next=/settings/account");
  }
  const { dict } = await getServerI18n();

  return (
    <main className="mx-auto w-full max-w-4xl px-4 py-8">
      <h1 className="border-b border-border pb-4 text-2xl font-bold">
        {dict.settingsProfile.accountPageTitle}
      </h1>
      <div className="mt-6 grid gap-8 md:grid-cols-[200px_1fr] md:items-start">
        <SettingsNav dict={dict} active="account" />
        <AccountForm user={user} />
      </div>
    </main>
  );
}
