import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { fetchWatchStateAction } from "@/actions/notifications.action";
import { EntityFeed } from "@/components/comments/entity-feed";
import { WatchButton } from "@/components/notifications/watch-button";
import { EntityNoticeBanner } from "@/components/notices/entity-notice-banner";
import { RequestNotice } from "@/components/notices/request-notice";
import { RequestDetailView } from "@/components/requests/request-detail";
import { getServerI18n } from "@/i18n/server";
import { listActivity, listComments } from "@/lib/feed.api";
import { listParts } from "@/lib/parts.api";
import { getRequest } from "@/lib/requests.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.requests.title} · PrintForHelp` };
}

export default async function RequestDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ from?: string }>;
}) {
  const { id } = await params;
  const { from } = await searchParams;
  const request = await getRequest(id);
  if (!request) {
    notFound();
  }

  const user = await getCurrentUser();
  const { dict } = await getServerI18n();
  const [parts, comments, activity, watching] = await Promise.all([
    listParts(),
    listComments("request", request.id),
    listActivity("request", request.id),
    user
      ? fetchWatchStateAction("request", request.id)
      : Promise.resolve(false),
  ]);

  const partNames: Record<string, string> = Object.fromEntries(
    parts.map((part) => [part.id, part.name]),
  );
  // Only active, non-discontinued parts can be added as new items.
  const activeParts = parts.filter(
    (part) => part.active && part.status === "active",
  );

  const isMaintainer = user?.role === "maintainer" || user?.role === "admin";
  const canManage =
    !!user && (user.id === request.requester_user_id || isMaintainer);
  const viewer = user ? { id: user.id, role: user.role } : null;
  const t = dict.requestDetail;
  // When the visitor arrived from My Contributions, send them back there
  // instead of the public requests list (`?from=contributions`).
  const fromContributions = from === "contributions";
  const backHref = fromContributions ? "/my-contributions" : "/requests";
  const backLabel = fromContributions ? t.backToContributions : t.back;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-center justify-between gap-4">
        <Link href={backHref} className="text-sm text-muted hover:underline">
          {backLabel}
        </Link>
        {user && (
          <WatchButton
            entityType="request"
            entityId={request.id}
            initialWatching={watching}
          />
        )}
      </div>
      <EntityNoticeBanner targetType="request" targetId={request.id} />
      {canManage && (
        <RequestNotice
          targetType="request"
          targetId={request.id}
          revalidate={`/requests/${request.id}`}
          isMaintainer={isMaintainer}
        />
      )}

      <div className="mt-6">
        <RequestDetailView
          request={request}
          parts={activeParts}
          partNames={partNames}
          isLoggedIn={!!user}
          canManage={canManage}
          initialWatching={watching}
        />
      </div>

      <section className="mt-10 flex flex-col gap-4">
        <div>
          <h2 className="text-lg font-semibold">{t.feedTitle}</h2>
          <p className="text-sm text-muted">{t.feedSubtitle}</p>
        </div>
        <EntityFeed
          revalidate={`/requests/${request.id}`}
          entityType="request"
          entityId={request.id}
          comments={comments}
          activity={activity}
          viewer={viewer}
        />
      </section>
    </main>
  );
}
