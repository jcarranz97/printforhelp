import type { Metadata } from "next";

import { previewUnsubscribeAction } from "@/actions/notification-prefs.action";
import { UnsubscribeConfirm } from "@/components/notifications/unsubscribe-confirm";
import { getServerI18n } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.notifications.unsubscribe.title} · PrintForHelp` };
}

export default async function UnsubscribePage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const { token } = await searchParams;
  const { dict } = await getServerI18n();
  const t = dict.notifications.unsubscribe;
  const description = token ? await previewUnsubscribeAction(token) : null;

  return (
    <main className="mx-auto w-full max-w-md px-4 py-12">
      <h1 className="text-2xl font-semibold">{t.title}</h1>
      <div className="mt-6">
        <UnsubscribeConfirm token={token ?? ""} description={description} />
      </div>
    </main>
  );
}
