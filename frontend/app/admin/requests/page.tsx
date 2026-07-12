import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { RequestQueue } from "@/components/admin/request-queue";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import { listReviewQueue } from "@/lib/requests.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.moderation.queueTitle} · PrintForHelp` };
}

/** Maintainer/admin queue of campaigns awaiting approval (FR-134). */
export default async function AdminRequestsPage() {
  const currentUser = await getCurrentUser();
  if (!currentUser) {
    redirect("/login?next=/admin/requests");
  }
  // A UX guard only — the API re-checks the role on every call (NFR-006).
  if (currentUser.role !== "admin" && currentUser.role !== "maintainer") {
    redirect("/");
  }

  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value ?? "";
  const requests = await listReviewQueue(token);
  const { dict } = await getServerI18n();

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">{dict.moderation.queueTitle}</h1>
        <p className="mt-1 text-sm text-muted">
          {dict.moderation.queueSubtitle}
        </p>
      </div>
      <RequestQueue requests={requests} />
    </main>
  );
}
